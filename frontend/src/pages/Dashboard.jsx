import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import AddProjectModal from '../components/AddProjectModal'
import { useSpacetimeDB } from '../hooks/useSpacetimeDB'
import { fetchProjects, createProject as createProjectApi } from '../lib/api'
import { Boxes, Activity, ArrowRight, Plus } from 'lucide-react'

export default function Dashboard() {
  const { projects, incidents, isConnected } = useSpacetimeDB();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [djangoProjects, setDjangoProjects] = useState(null);
  const [projectsLoadError, setProjectsLoadError] = useState(null);

  const refreshDjangoProjects = useCallback(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setDjangoProjects(null);
      return;
    }
    setProjectsLoadError(null);
    fetchProjects(token)
      .then(setDjangoProjects)
      .catch((err) => {
        setProjectsLoadError(err.message || 'Failed to load projects');
        setDjangoProjects([]);
      });
  }, []);

  useEffect(() => {
    refreshDjangoProjects();
  }, [refreshDjangoProjects]);

  const useDjangoList = localStorage.getItem('token') != null && djangoProjects != null;
  const projectList = useDjangoList ? djangoProjects : Object.values(projects);
  const incidentList = Object.values(incidents);

  const activeIncidentsCount = incidentList.filter(inc => inc.status === 'error').length;

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col">
      <Navbar showLogout={true} />
      
      {!isConnected && (
         <div className="bg-error/10 text-error border-b border-error/20 px-4 py-2 text-center text-[10px] font-bold uppercase tracking-widest">
           Offline: Reconnecting to SpacetimeDB...
         </div>
      )}

      <main className="flex-1 p-8 max-w-6xl mx-auto w-full">
        {/* Hero Section */}
        <div className="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-10 h-10 rounded-xl bg-[#171717] flex items-center justify-center shadow-lg">
                 <Boxes className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-3xl font-black text-[#171717] tracking-tight">Control Center</h1>
            </div>
            <p className="text-[#737373] max-w-md text-sm font-medium">
              Manage your autonomous monitoring agents across multiple clusters.
            </p>
          </div>

          <button 
            onClick={() => setIsModalOpen(true)}
            className="px-6 py-3 bg-[#171717] hover:bg-[#262626] text-white rounded-xl shadow-lg font-bold text-xs uppercase tracking-widest flex items-center gap-2 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <Plus className="w-5 h-5" /> New Project
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="bg-white border border-[#E5E5E5] p-6 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
            <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest block mb-2">Active Projects</span>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-black text-[#171717]">{projectList.length}</span>
              <span className="text-xs font-bold text-success bg-success/10 px-2 py-0.5 rounded-full">Online</span>
            </div>
          </div>
          <div className="bg-white border border-[#E5E5E5] p-6 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
            <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest block mb-2">Live Incidents</span>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-black text-[#171717]">{activeIncidentsCount}</span>
              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${activeIncidentsCount > 0 ? 'bg-error/10 text-error' : 'bg-success/10 text-success'}`}>
                {activeIncidentsCount > 0 ? 'Critical' : 'Nominal'}
              </span>
            </div>
          </div>
          <div className="bg-white border border-[#E5E5E5] p-6 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
            <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest block mb-2">Fleet Health</span>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-black text-[#171717]">99.8</span>
              <span className="text-xs font-bold text-[#737373] bg-[#F5F5F5] px-2 py-0.5 rounded-full">% SLA</span>
            </div>
          </div>
        </div>
        
        {/* Project Grid */}
        <div className="flex items-center gap-4 mb-8">
          <h2 className="text-xl font-bold text-[#171717] shrink-0">Your Fleet</h2>
          <div className="flex-1 h-px bg-gradient-to-r from-[#E5E5E5] to-transparent" />
        </div>

        {projectsLoadError && (
          <div className="mb-6 rounded-xl border border-error/30 bg-error/5 px-4 py-3 text-sm text-error">
            {projectsLoadError}
          </div>
        )}

        {projectList.length === 0 && (isConnected || useDjangoList) ? (
          <div className="text-center py-24 bg-white border border-dashed border-[#E5E5E5] rounded-[2rem]">
             <Boxes className="w-16 h-16 text-[#E5E5E5] mx-auto mb-4" />
             <h3 className="text-xl font-bold text-[#737373]">No Projects Configured</h3>
             <p className="text-sm text-[#A3A3A3] mt-2">Initialize your first service monitor to begin deployment.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {projectList.map(project => {
              const projectIncidents = incidentList.filter(inc => String(inc.project_id) === String(project.id));
              const hasAlert = projectIncidents.some(inc => inc.status === 'error');

              return (
                <Link 
                  key={project.id} 
                  to={`/project/${project.id}`}
                  className="group bg-white border border-[#E5E5E5] rounded-[2rem] p-8 shadow-sm hover:shadow-2xl transition-all hover:-translate-y-1 hover:border-[#171717] flex flex-col relative overflow-hidden"
                >
                  {hasAlert && (
                    <div className="absolute top-6 right-6">
                       <div className="w-3 h-3 rounded-full bg-error shadow-[0_0_12px_rgba(239,68,68,0.5)] animate-pulse" />
                    </div>
                  )}

                  <div className="mb-6">
                     <div className="w-12 h-12 rounded-2xl bg-[#F5F5F5] group-hover:bg-[#171717] flex items-center justify-center transition-all duration-300 mb-6 group-hover:rotate-[10deg]">
                        <Activity className="w-6 h-6 text-[#737373] group-hover:text-white" />
                     </div>
                     <h3 className="text-2xl font-black text-[#171717] leading-tight mb-2">{project.name}</h3>
                     <p className="text-sm text-[#737373] line-clamp-2 leading-relaxed font-medium">
                        {project.description}
                     </p>
                  </div>

                  <div className="mt-auto pt-6 flex items-center justify-between border-t border-[#F5F5F5]">
                    <div className="flex flex-col">
                       <span className="text-[10px] font-black text-[#A3A3A3] uppercase tracking-widest mb-1">State Log</span>
                       <span className="text-sm font-bold text-[#171717]">{projectIncidents.length} Records</span>
                    </div>
                    <div className="w-10 h-10 rounded-full bg-[#FAFAFA] group-hover:bg-[#171717] group-hover:text-white transition-all flex items-center justify-center">
                       <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
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
            await createProjectApi(token, data);
            refreshDjangoProjects();
          } catch (err) {
            window.alert(err.message || 'Could not create project');
          }
        }} 
      />
    </div>
  )
}
