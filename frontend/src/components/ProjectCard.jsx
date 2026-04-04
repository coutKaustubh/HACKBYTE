import { useNavigate } from 'react-router-dom'
import { Clock } from 'lucide-react'

export default function ProjectCard({ project }) {
  const navigate = useNavigate()

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-5 rounded-lg flex flex-col h-full hover:border-accent/50 transition-colors">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-bold text-[#171717] tracking-tight">
          {project.name}
        </h3>
      </div>
      
      <div className="text-sm text-[#737373] mb-6 flex-grow">
        <div className="flex items-center gap-1.5 mb-2">
          <Clock className="w-4 h-4" />
          <span>Last activity: {project.lastActivity}</span>
        </div>
      </div>
      
      <button 
        onClick={() => navigate(`/project/${project.id}`)}
        className="w-full py-2 bg-[#FAFAFA] border border-[#E5E5E5] text-[#171717] rounded hover:bg-border/50 transition-colors shadow-sm text-sm"
      >
        Open
      </button>
    </div>
  )
}
