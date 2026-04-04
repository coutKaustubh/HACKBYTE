import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import { useSpacetimeDB } from '../hooks/useSpacetimeDB'
import { Layout, Boxes, Terminal as TermIcon, Shield, Activity, ArrowRight, Plus } from 'lucide-react'

export default function Dashboard() {
  const { projects, incidents, isConnected } = useSpacetimeDB();
  
  const projectList = Object.values(projects);
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
              <div className="w-8 h-8 rounded-lg bg-[#171717] flex items-center justify-center">
                 <Boxes className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-3xl font-bold text-[#171717]">Control Center</h1>
            </div>
            <p className="text-[#737373] max-w-md">
              Manage your autonomous monitoring agents across multiple service clusters.
            </p>
          </div>

          <button className="px-5 py-2.5 bg-[#171717] hover:bg-[#262626] text-white rounded-lg shadow-sm font-bold text-xs uppercase tracking-widest flex items-center gap-2 transition-all hover:scale-[1.02]">
            <Plus className="w-4 h-4" /> New Project
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="bg-white border border-[#E5E5E5] p-6 rounded-2xl shadow-sm">
            <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest block mb-1">Active Projects</span>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-black text-[#171717]">{projectList.length}</span>
              <span className="text-xs font-bold text-success">Online</span>
            </div>
          </div>
          <div className="bg-white border border-[#E5E5E5] p-6 rounded-2xl shadow-sm">
            <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest block mb-1">Live Incidents</span>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-black text-[#171717]">{activeIncidentsCount}</span>
              <span className={`text-xs font-bold ${activeIncidentsCount > 0 ? 'text-error' : 'text-success'}`}>
                {activeIncidentsCount > 0 ? 'Critical' : 'Nominal'}
              </span>
            </div>
          </div>
          <div className="bg-white border border-[#E5E5E5] p-6 rounded-2xl shadow-sm">
            <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest block mb-1">Fleet Health</span>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-black text-[#171717]">99.8</span>
              <span className="text-xs font-bold text-[#737373]">% SLA</span>
            </div>
          </div>
        </div>
        
        {/* Project Grid */}
        <h2 className="text-lg font-bold text-[#171717] mb-6 flex items-center gap-2">
          Your Projects
          <div className="flex-1 h-px bg-[#E5E5E5]" />
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projectList.length === 0 && isConnected ? (
            <div className="col-span-full text-center py-24 bg-white border border-dashed border-[#E5E5E5] rounded-3xl">
               <Boxes className="w-12 h-12 text-[#E5E5E5] mx-auto mb-4" />
               <h3 className="text-xl font-bold text-[#737373]">No Projects Configured</h3>
               <p className="text-sm text-[#A3A3A3] mt-2">Initialize your first service monitor to begin.</p>
            </div>
          ) : (
            projectList.map(project => {
              const projectIncidents = incidentList.filter(inc => String(inc.project_id) === String(project.id));
              const hasAlert = projectIncidents.some(inc => inc.status === 'error');

              return (
                <Link 
                  key={project.id} 
                  to={`/project/${project.id}`}
                  className="group bg-white border border-[#E5E5E5] rounded-3xl p-6 shadow-sm hover:shadow-xl transition-all hover:border-[#171717] flex flex-col relative overflow-hidden"
                >
                  {hasAlert && (
                    <div className="absolute top-0 right-0 p-3">
                       <div className="w-2 h-2 rounded-full bg-error animate-ping" />
                    </div>
                  )}

                  <div className="mb-4">
                     <div className="w-10 h-10 rounded-xl bg-[#F5F5F5] group-hover:bg-[#171717] flex items-center justify-center transition-colors mb-4">
                        <Activity className="w-5 h-5 text-[#737373] group-hover:text-white" />
                     </div>
                     <h3 className="text-xl font-bold text-[#171717] group-hover:translate-x-1 transition-transform">{project.name}</h3>
                     <p className="text-sm text-[#737373] mt-2 line-clamp-2 leading-relaxed">
                        {project.description}
                     </p>
                  </div>

                  <div className="mt-auto pt-6 flex items-center justify-between border-t border-[#F5F5F5]">
                    <div className="flex flex-col">
                       <span className="text-[9px] font-bold text-[#A3A3A3] uppercase tracking-widest">Active Logs</span>
                       <span className="text-xs font-bold text-[#171717]">{projectIncidents.length} Records</span>
                    </div>
                    <div className="p-2 rounded-full bg-[#FAFAFA] group-hover:bg-[#171717] group-hover:text-white transition-all">
                       <ArrowRight className="w-4 h-4" />
                    </div>
                  </div>
                </Link>
              )
            })
          )}
        </div>
      </main>
    </div>
  )
}
