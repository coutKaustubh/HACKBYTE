import { useEffect, useState } from 'react'
import Navbar from '../components/Navbar'
import ProjectCard from '../components/ProjectCard'
import AddProjectModal from '../components/AddProjectModal'
import { useNavigate } from 'react-router-dom'

const DUMMY_PROJECTS = [
  { id: 'proj_1', name: 'api-gateway', status: 'Active', lastActivity: '2 mins ago' },
  { id: 'proj_2', name: 'auth-service', status: 'Idle', lastActivity: '5 hours ago' },
  { id: 'proj_3', name: 'billing-worker', status: 'Active', lastActivity: '1 day ago' },
  { id: 'proj_4', name: 'frontend-dashboard', status: 'Idle', lastActivity: '3 days ago' },
]

export default function Dashboard() {
  const navigate = useNavigate();
  const [userName, setUserName] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('token');
    // if (!token) {
    //   navigate('/');
    //   return;
    // }

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
          <button 
            onClick={() => setIsModalOpen(true)}
            className="text-sm px-4 py-2 bg-[#171717] text-white font-medium rounded-lg shadow-md hover:bg-black transition-colors cursor-pointer flex items-center gap-2"
          >
            + Add Project
          </button>
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
        onSubmit={(data) => {
          console.log("New Project Data:", data);
          // TODO: send form data to backend
        }} 
      />
    </div>
  )
}
