import { Link } from 'react-router-dom'
import { Activity } from 'lucide-react'

export default function Navbar({ projectName, status }) {
  return (
    <nav className="h-14 border-b border-[#E5E5E5] bg-[#FFFFFF]/50 flex items-center px-6 justify-between">
      <Link to="/dashboard" className="flex items-center gap-2">
        <Activity className="w-5 h-5 text-accent" />
        <span className="font-semibold text-[#171717]">Patchify</span>
      </Link>
      
      {projectName && (
        <div className="flex items-center gap-4">
          <span className="text-[#737373] text-sm">{projectName}</span>
          {status && (
            <span className={`text-xs px-2 py-0.5 rounded-full border ${status === 'Active' ? 'border-success text-success bg-success/10' : status === 'error' || status === 'Error' ? 'border-error text-error bg-error/10' : 'border-[#E5E5E5] text-[#737373]'}`}>
              {status}
            </span>
          )}
        </div>
      )}
    </nav>
  )
}
