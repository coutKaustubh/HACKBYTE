import { useEffect } from 'react'
import Navbar from '../components/Navbar'
import ProjectCard from '../components/ProjectCard'
import { useNavigate } from 'react-router-dom'

const DUMMY_PROJECTS = [
  { id: 'proj_1', name: 'api-gateway', status: 'Active', lastActivity: '2 mins ago' },
  { id: 'proj_2', name: 'auth-service', status: 'Idle', lastActivity: '5 hours ago' },
  { id: 'proj_3', name: 'billing-worker', status: 'Active', lastActivity: '1 day ago' },
  { id: 'proj_4', name: 'frontend-dashboard', status: 'Idle', lastActivity: '3 days ago' },
]

export default function Dashboard() {
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/');
    }
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col">
      <Navbar />
      
      <main className="flex-1 p-8 max-w-6xl mx-auto w-full">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-[#171717]">Projects</h1>
          <button 
            onClick={handleLogout}
            className="text-sm px-4 py-2 bg-white border border-[#E5E5E5] text-red-600 font-medium rounded shadow-sm hover:bg-red-50 transition-colors cursor-pointer"
          >
            Logout
          </button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {DUMMY_PROJECTS.map(project => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      </main>
    </div>
  )
}
