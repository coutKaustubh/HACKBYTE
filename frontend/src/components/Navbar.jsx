import { Link, useLocation } from 'react-router-dom'
import { Activity, Database } from 'lucide-react'

export default function Navbar({ projectName, showLogout, onLogout }) {
  return (
    <nav className="h-14 border-b border-[#E5E5E5] bg-[#FFFFFF]/50 flex items-center px-6 justify-between">
      <Link to="/dashboard" className="flex items-center gap-2">
        <img src="/Xone.png" alt="XOne Logo" className="w-6 h-6 object-contain" />
        <span className="font-semibold text-[#171717]">XOne</span>
      </Link>
      
      <div className="flex items-center gap-4 flex-1 justify-end">
        <Link 
          to="/project-data" 
          className="text-sm font-medium text-[#737373] hover:text-[#171717] flex items-center gap-2 mr-4"
        >
          <Database className="w-4 h-4" />
          SQL Monitor
        </Link>
        {projectName && (
          <div className="flex items-center gap-4 pr-2">
            <span className="text-[#737373] font-medium text-sm">{projectName}</span>
          </div>
        )}
        
        {showLogout && (
          <>
            {projectName && <div className="h-4 w-px bg-border hidden sm:block"></div>}
            <button 
              onClick={onLogout}
              className="text-sm px-4 py-1.5 bg-white border border-[#E5E5E5] text-red-600 font-medium rounded shadow-sm hover:bg-red-50 transition-colors cursor-pointer"
            >
              Logout
            </button>
          </>
        )}
      </div>
    </nav>
  )
}
