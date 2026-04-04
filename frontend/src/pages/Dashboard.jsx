import { useEffect, useState } from 'react'
import Navbar from '../components/Navbar'
import ProjectCard from '../components/ProjectCard'
import { useNavigate } from 'react-router-dom'

const DUMMY_PROJECTS = [
  { id: 'proj_1', name: 'api-gateway', lastActivity: '2 mins ago' },
  { id: 'proj_2', name: 'auth-service', lastActivity: '5 hours ago' },
  { id: 'proj_3', name: 'billing-worker', lastActivity: '1 day ago' },
  { id: 'proj_4', name: 'frontend-dashboard', lastActivity: '3 days ago' },
]

export default function Dashboard() {
  const navigate = useNavigate();
  const [userName, setUserName] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/');
      return;
    }

    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));

      const decoded = JSON.parse(jsonPayload);
      setUserName(decoded.name || decoded.username || decoded.email || 'User');
    } catch (e) {
      console.error("Failed to decode JWT:", e);
      setUserName('User');
    }
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col">
      <Navbar showLogout={true} onLogout={handleLogout} />

      <main className="flex-1 p-8 max-w-6xl mx-auto w-full">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-[#171717] mb-1">Hello, {userName}</h1>
            <p className="text-[#737373]">Here are your active projects.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
          {DUMMY_PROJECTS.map(project => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      </main>

      <AddProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={async (data) => {
          const token = localStorage.getItem('token');
          if (!token) {
            window.alert('Sign in first so your project can be saved to your account.');
            return;
          }

          try {
            // 1️⃣ Save to Postgres via Django API
            const created = await createProjectApi(token, data);
            console.log('[Django] Created project:', created);

            // Refresh the list from Django right away
            refreshDjangoProjects();
            setIsModalOpen(false);

            // 2️⃣ Mirror into SpacetimeDB via direct HTTP call
            // (avoids BigInt/SDK serialization issues entirely)
            try {
              const payload = decodeJwtPayload(token);
              // Map JWT user id → number (fallback 1)
              const userId = parseInt(String(payload.user_id ?? payload.sub ?? '1'), 10) || 1;
              // Map returned project id → number (fallback 0)
              const projectId = parseInt(String(created?.id ?? created?.pk ?? '0'), 10) || 0;

              console.log('[STDB HTTP] Calling create_project →', { userId, projectId, name: data.name });

              // Args order must match the reducer definition:
              // (user_id u64, django_project_id u64, name, description, ssh_key, server_ip, root_directory, deploy_commands)
              await callStdbReducer('create_project', {
                user_id: userId,
                django_project_id: projectId,
                name: data.name || '',
                description: data.description || '',
                ssh_key: data.sshKey || '',
                server_ip: data.serverIp || '',
                root_directory: data.rootDirectory || '',
                deploy_commands: data.userDeployCommands || 'npm install && npm run build && npm start',
              });
              console.log('[STDB HTTP] create_project ✓');
            } catch (stdbErr) {
              console.warn('[STDB HTTP] Mirror failed (non-fatal):', stdbErr.message);
            }
          } catch (err) {
            console.error('[Project create error]', err);
            window.alert(err.message || 'Could not create project');
          }
        }}
      />
    </div>
  )
}
