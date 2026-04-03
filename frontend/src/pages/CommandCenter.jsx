import { useParams } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Terminal from '../components/Terminal'
import DiagnosisPanel from '../components/DiagnosisPanel'

export default function CommandCenter() {
  const { id } = useParams()
  
  // Create a display name based on the id route param 
  const projectName = (id && id.startsWith('proj_')) 
                        ? 'Project ' + id.replace('proj_', '') 
                        : 'api-gateway'
  
  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col">
      <Navbar projectName={projectName} status="error" />
      
      <main className="flex-1 p-6 w-full max-w-7xl mx-auto flex flex-col lg:flex-row gap-6">
        <div className="w-full lg:w-[70%] h-[600px] lg:h-auto min-h-[500px]">
          <Terminal />
        </div>
        <div className="w-full lg:w-[30%] lg:h-auto">
          <DiagnosisPanel />
        </div>
      </main>
    </div>
  )
}
