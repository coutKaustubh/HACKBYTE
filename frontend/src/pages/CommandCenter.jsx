import { useRef, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import Terminal from '../components/Terminal'
import DiagnosisPanel from '../components/DiagnosisPanel'
import SQLMonitor from '../components/SQLMonitor'
import { useSpacetimeDB } from '../hooks/useSpacetimeDB'
import { ArrowLeft, Layout, Terminal as TermIcon, Shield, Activity } from 'lucide-react'
import { logToBlockchain } from '../lib/logToBlockchain'

export default function CommandCenter() {
  const { id: projectId } = useParams()
  
  const { incidents, executions, aiDecisions, safetyChecks, isConnected, startExecution, projects } = useSpacetimeDB();
  
  const currentProject = projects[projectId];

  // Filter incidents for this project
  const projectIncidents = Object.values(incidents)
    .filter(inc => String(inc.project_id) === String(projectId))
    .sort((a,b) => Number(a.id) - Number(b.id));

  const currentIncident = projectIncidents[projectIncidents.length - 1]; // latest
  
  const incidentId = currentIncident?.id;
  const currentAiDecision = aiDecisions[incidentId];
  const currentSafetyCheck = safetyChecks[incidentId];
  const currentExecution = executions[incidentId];

  const overallStatus = currentIncident?.status === 'resolved' ? 'success' : 'error';

  // ── Blockchain audit log: fires once when incident is resolved ──────────
  const loggedIncidentRef = useRef(null);

  useEffect(() => {
    // Only fire when status is resolved and we haven't already logged this incident
    if (overallStatus !== 'success') return;
    if (!currentIncident?.id) return;
    if (loggedIncidentRef.current === currentIncident.id) return;

    loggedIncidentRef.current = currentIncident.id;

    const payload = {
      projectId: String(projectId),
      incidentId: String(currentIncident.id),
      status: 'PATCH_SUCCESSFUL',
      patchedAt: new Date().toISOString(),
      aiDecision: currentAiDecision ?? null,
      safetyCheck: currentSafetyCheck ?? null,
      execution: currentExecution ?? null,
    };

    logToBlockchain(String(projectId), payload)
      .then(({ cid, txHash }) => {
        console.log(`🎉 Audit log complete — CID: ${cid} | TX: ${txHash}`);
      })
      .catch((err) => {
        console.error('❌ Blockchain log failed:', err.message);
      });
  }, [overallStatus, currentIncident?.id]);

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col h-screen overflow-hidden">
      {/* Custom Project Header (Replaces Navbar) */}
      <header className="h-16 border-b border-[#E5E5E5] bg-white flex items-center px-6 justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link to="/dashboard" className="p-2 hover:bg-[#F5F5F5] rounded-full transition-colors text-[#737373] hover:text-[#171717]">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="w-px h-6 bg-[#E5E5E5]" />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-[#171717] tracking-tight">{currentProject?.name || 'Loading...'}</h1>
              <span className="text-[10px] font-bold bg-[#F5F5F5] text-[#737373] px-1.5 py-0.5 rounded border border-[#E5E5E5] uppercase tracking-widest">
                ID: {projectId}
              </span>
            </div>
            <p className="text-[11px] text-[#737373] font-medium leading-none mt-0.5">
              {currentProject?.description || 'Project Monitoring Active'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6">
           <div className="flex items-center gap-4">
              <div className="flex flex-col items-end">
                <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest">Engine Status</span>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success animate-pulse' : 'bg-error'}`} />
                  <span className="text-xs font-bold text-[#171717]">{isConnected ? 'ONLINE' : 'OFFLINE'}</span>
                </div>
              </div>
           </div>
           <div className={`px-4 py-1.5 rounded-md border font-bold text-xs uppercase tracking-widest
             ${overallStatus === 'success' ? 'bg-success/10 text-success border-success/30' : 'bg-error/10 text-error border-error/30'}`}>
             {overallStatus === 'success' ? 'System Nominal' : 'Incident Active'}
           </div>
        </div>
      </header>

      {/* Main Grid View */}
      <main className="flex-1 p-6 grid grid-cols-12 gap-6 overflow-hidden bg-[#F8F8F8]">
        
        {/* Left Column: Live Terminal & SQL Monitor (Replacing traditional layout) */}
        <div className="col-span-12 lg:col-span-8 flex flex-col gap-6 overflow-hidden">
          
          <div className="flex-1 min-h-[300px]">
             <Terminal 
                incident={currentIncident}
                aiDecision={currentAiDecision}
                safetyCheck={currentSafetyCheck}
                execution={currentExecution}
             />
          </div>

          <div className="h-[40%] min-h-[300px]">
             <SQLMonitor projectId={projectId} />
          </div>

        </div>

        {/* Right Column: Diagnosis Panel */}
        <div className="col-span-12 lg:col-span-4 flex flex-col overflow-hidden">
          <DiagnosisPanel 
            incident={currentIncident}
            aiDecision={currentAiDecision}
            safetyCheck={currentSafetyCheck}
            execution={currentExecution}
            onStartExecution={() => startExecution(incidentId)}
          />
        </div>

      </main>
    </div>
  )
}
