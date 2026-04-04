import { useEffect, useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import AddProjectModal from '../components/AddProjectModal'
import { useSpacetimeDB } from '../hooks/useSpacetimeDB'
import { fetchProjects, createProject as createProjectApi } from '../lib/api'
import { Boxes, Activity, ArrowRight, Plus } from 'lucide-react'

function decodeJwtPayload(token) {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(base64))
  } catch {
    return {}
  }
}

async function callStdbReducer(reducerName, args) {
  const url = `http://127.0.0.1:3000/v1/database/realitypatch-db-2lsay/call/${reducerName}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(args),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.status);
    throw new Error(`SpacetimeDB ${reducerName} failed: ${text}`);
  }
  return res;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { projects, incidents, isConnected } = useSpacetimeDB();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [djangoProjects, setDjangoProjects] = useState(null);
  const [projectsLoadError, setProjectsLoadError] = useState(null);
  const [userName, setUserName] = useState('');

  const refreshDjangoProjects = useCallback(() => {
    const token = localStorage.getItem('token');
    if (!token) { setDjangoProjects(null); return; }
    setProjectsLoadError(null);
    fetchProjects(token)
      .then(setDjangoProjects)
      .catch((err) => {
        setProjectsLoadError(err.message || 'Failed to load projects');
        setDjangoProjects([]);
      });
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { navigate('/'); return; }
    try {
      const payload = decodeJwtPayload(token);
      setUserName(payload.name || payload.username || payload.email || 'User');
    } catch { setUserName('User'); }
    refreshDjangoProjects();
  }, [navigate, refreshDjangoProjects]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
  };

  const useDjangoList = localStorage.getItem('token') != null && djangoProjects != null;
  const projectList = useDjangoList ? djangoProjects : Object.values(projects);
  const incidentList = Object.values(incidents);
  const activeIncidentsCount = incidentList.filter(inc => inc.status === 'error').length;

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col">
      <Navbar showLogout={true} onLogout={handleLogout} />

      {!isConnected && (
        <div className="bg-red-50 text-red-600 border-b border-red-200 px-4 py-2 text-center text-[10px] font-bold uppercase tracking-widest">
          Offline: Reconnecting to SpacetimeDB...
        </div>
      )}

      <main className="flex-1 p-8 max-w-6xl mx-auto w-full">
        <div className="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-10 h-10 rounded-xl bg-[#171717] flex items-center justify-center shadow-lg">
                <Boxes className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-3xl font-black text-[#171717] tracking-tight">Hello, {userName || 'Control Center'}</h1>
            </div>
            <p className="text-[#737373] max-w-md text-sm font-medium">Manage your autonomous monitoring agents across multiple clusters.</p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-6 py-3 bg-[#171717] hover:bg-[#262626] text-white rounded-xl shadow-lg font-bold text-xs uppercase tracking-widest flex items-center gap-2 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <Plus className="w-5 h-5" /> New Project
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="bg-white border border-[#E5E5E5] p-6 rounded-2xl shadow-sm">
            <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest block mb-2">Active Projects</span>
            <span className="text-4xl font-black text-[#171717]">{projectList.length}</span>
          </div>
          <div className="bg-white border border-[#E5E5E5] p-6 rounded-2xl shadow-sm">
            <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest block mb-2">Live Incidents</span>
            <span className="text-4xl font-black text-[#171717]">{activeIncidentsCount}</span>
          </div>
          <div className="bg-white border border-[#E5E5E5] p-6 rounded-2xl shadow-sm">
            <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest block mb-2">Fleet Health</span>
            <span className="text-4xl font-black text-[#171717]">99.8<span className="text-lg font-bold text-[#737373]">%</span></span>
          </div>
        </div>

        {projectsLoadError && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">{projectsLoadError}</div>
        )}

        {projectList.length === 0 ? (
          <div className="text-center py-24 bg-white border border-dashed border-[#E5E5E5] rounded-[2rem]">
            <Boxes className="w-16 h-16 text-[#E5E5E5] mx-auto mb-4" />
            <h3 className="text-xl font-bold text-[#737373]">No Projects Configured</h3>
            <p className="text-sm text-[#A3A3A3] mt-2">Click New Project to add your first deployment.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {projectList.map(project => {
              const projectIncidents = incidentList.filter(inc => String(inc.project_id) === String(project.id));
              const hasAlert = projectIncidents.some(inc => inc.status === 'error');
              return (
                <Link key={project.id} to={`/project/${project.id}`}
                  className="group bg-white border border-[#E5E5E5] rounded-[2rem] p-8 shadow-sm hover:shadow-2xl transition-all hover:-translate-y-1 hover:border-[#171717] flex flex-col relative overflow-hidden"
                >
                  {hasAlert && <div className="absolute top-6 right-6 w-3 h-3 rounded-full bg-red-500 animate-pulse" />}
                  <div className="w-12 h-12 rounded-2xl bg-[#F5F5F5] group-hover:bg-[#171717] flex items-center justify-center transition-all mb-6">
                    <Activity className="w-6 h-6 text-[#737373] group-hover:text-white" />
                  </div>
                  <h3 className="text-2xl font-black text-[#171717] mb-2">{project.name}</h3>
                  <p className="text-sm text-[#737373] line-clamp-2 font-medium">{project.description}</p>
                  <div className="mt-auto pt-6 flex items-center justify-between border-t border-[#F5F5F5]">
                    <span className="text-sm font-bold text-[#171717]">{projectIncidents.length} Records</span>
                    <div className="w-10 h-10 rounded-full bg-[#FAFAFA] group-hover:bg-[#171717] group-hover:text-white transition-all flex items-center justify-center">
                      <ArrowRight className="w-5 h-5" />
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
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
