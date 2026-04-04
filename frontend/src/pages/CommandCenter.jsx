import { useState, useCallback, useRef, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import Terminal from '../components/Terminal'
import DiagnosisPanel from '../components/DiagnosisPanel'
import SQLMonitor from '../components/SQLMonitor'
import { useSpacetimeDB } from '../hooks/useSpacetimeDB'
import { runAgent } from '../lib/api'
import { ArrowLeft, Loader2, CheckCircle2, XCircle, Zap } from 'lucide-react'

export default function CommandCenter() {
  const { id: projectId } = useParams()
  const { incidents, executions, aiDecisions, safetyChecks, agentEvents, isConnected, projects, resolveIncident } = useSpacetimeDB();

  // Run Agent state
  const [agentRunning, setAgentRunning] = useState(false)
  const [agentResult, setAgentResult] = useState(null)   // { incident_id, summary, resolved }
  const [agentError, setAgentError] = useState(null)

  const currentProject = projects[projectId];

  // Filter incidents for this project (keyed by django_project_id in SpacetimeDB)
  const projectIncidents = Object.values(incidents)
    .filter(inc => String(inc.projectId ?? inc.project_id) === String(projectId))
    .sort((a, b) => Number(a.id) - Number(b.id));

  const currentIncident = projectIncidents[projectIncidents.length - 1]; // latest
  // ai_decision.incidentId is a u64 FK → matches incident.id (numeric)
  const currentAiDecision = aiDecisions[Number(currentIncident?.id)];
  const currentSafetyCheck = safetyChecks[currentIncident?.id];
  const currentExecution = executions[currentIncident?.id];

  // ── DEBUG ────────────────────────────────────────────────────────────────────
  console.log('[CC] projectIncidents:', projectIncidents);
  console.log('[CC] currentIncident:', currentIncident, '→ id:', currentIncident?.id);
  console.log('[CC] aiDecisions map keys:', Object.keys(aiDecisions));
  console.log('[CC] currentAiDecision:', currentAiDecision);
  // ─────────────────────────────────────────────────────────────────────────────

  // Filter live agent events for this project (most recent 20)
  const projectAgentEvents = Object.values(agentEvents)
    .filter(e => String(e.projectId ?? e.project_id) === String(projectId))
    .sort((a, b) => Number(a.id) - Number(b.id))
    .slice(-20);

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
  const handleRunAgent = useCallback(async () => {
    const token = localStorage.getItem('token')
    if (!token) {
      setAgentError('You must be signed in to run the agent.')
      return
    }
    setAgentRunning(true)
    setAgentResult(null)
    setAgentError(null)
    try {
      const result = await runAgent(token, projectId)
      setAgentResult(result)
    } catch (err) {
      setAgentError(err.message || 'Agent run failed')
    } finally {
      setAgentRunning(false)
    }
  }, [projectId])

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <header className="h-16 border-b border-[#E5E5E5] bg-white flex items-center px-6 justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link to="/dashboard" className="p-2 hover:bg-[#F5F5F5] rounded-full transition-colors text-[#737373] hover:text-[#171717]">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="w-px h-6 bg-[#E5E5E5]" />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-[#171717] tracking-tight">{currentProject?.name || `Project #${projectId}`}</h1>
              <span className="text-[10px] font-bold bg-[#F5F5F5] text-[#737373] px-1.5 py-0.5 rounded border border-[#E5E5E5] uppercase tracking-widest">
                ID: {projectId}
              </span>
            </div>
            <p className="text-[11px] text-[#737373] font-medium leading-none mt-0.5">
              {currentProject?.description || 'Project Monitoring Active'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Engine Status */}
          <div className="flex flex-col items-end">
            <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest">Engine</span>
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="text-xs font-bold text-[#171717]">{isConnected ? 'LIVE' : 'OFFLINE'}</span>
            </div>
          </div>

          {/* Incident Status Badge */}
          <div className={`px-4 py-1.5 rounded-md border font-bold text-xs uppercase tracking-widest
            ${overallStatus === 'success' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-600 border-red-200'}`}>
            {overallStatus === 'success' ? 'Nominal' : 'Incident Active'}
          </div>

          {/* Run Agent Button */}
          <button
            onClick={handleRunAgent}
            disabled={agentRunning}
            className="flex items-center gap-2 px-5 py-2 bg-[#171717] hover:bg-[#262626] disabled:bg-[#A3A3A3] text-white rounded-xl font-bold text-xs uppercase tracking-widest transition-all hover:scale-[1.02] active:scale-[0.98] disabled:cursor-not-allowed shadow-lg"
          >
            {agentRunning
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Running...</>
              : <><Zap className="w-4 h-4" /> Run Agent</>
            }
          </button>
        </div>
      </header>

      {/* Agent Result / Error Banner */}
      {agentResult && (
        <div className="shrink-0 bg-green-50 border-b border-green-200 px-6 py-2.5 flex items-center gap-3">
          <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="text-xs font-bold text-green-700 uppercase tracking-widest mr-3">
              {agentResult.resolved ? 'Resolved' : 'Completed'}
            </span>
            <span className="text-xs text-green-700 truncate">{agentResult.summary}</span>
          </div>
          <span className="text-[10px] text-green-600 font-mono shrink-0">{agentResult.incident_id}</span>
          <button onClick={() => setAgentResult(null)} className="text-green-400 hover:text-green-700 ml-2">✕</button>
        </div>
      )}
      {agentError && (
        <div className="shrink-0 bg-red-50 border-b border-red-200 px-6 py-2.5 flex items-center gap-3">
          <XCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span className="text-xs font-bold text-red-700 flex-1">{agentError}</span>
          <button onClick={() => setAgentError(null)} className="text-red-400 hover:text-red-700 ml-2">✕</button>
        </div>
      )}

      {/* Main Grid */}
      <main className="flex-1 p-6 grid grid-cols-12 gap-6 overflow-hidden bg-[#F8F8F8]">

        {/* Left: Terminal + SQL Monitor */}
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

        {/* Right: Diagnosis Panel + Live Agent Events */}
        <div className="col-span-12 lg:col-span-4 flex flex-col gap-4 overflow-hidden">
          <DiagnosisPanel
            incident={currentIncident}
            aiDecision={currentAiDecision}
            safetyCheck={currentSafetyCheck}
            execution={currentExecution}
          />

          {/* Live Agent Events Feed */}
          {projectAgentEvents.length > 0 && (
            <div className="bg-white border border-[#E5E5E5] rounded-2xl overflow-hidden flex flex-col" style={{ maxHeight: '220px' }}>
              <div className="px-4 py-3 border-b border-[#F5F5F5] flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest">Live Events</span>
                <span className="ml-auto text-[10px] font-bold text-[#A3A3A3]">{projectAgentEvents.length} recent</span>
              </div>
              <div className="overflow-y-auto flex-1 divide-y divide-[#F5F5F5]">
                {[...projectAgentEvents].reverse().map(event => (
                  <div key={event.id} className="px-4 py-2 flex items-start gap-2">
                    <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded shrink-0 mt-0.5 ${event.eventType === 'ACTION_BLOCKED' || event.eventType === 'ACTION_FAILED'
                      ? 'bg-red-50 text-red-600'
                      : event.eventType === 'INCIDENT_RESOLVED'
                        ? 'bg-green-50 text-green-700'
                        : event.eventType === 'AGENT_THINKING'
                          ? 'bg-purple-50 text-purple-700'
                          : 'bg-[#F5F5F5] text-[#737373]'
                      }`}>{(event.eventType || '').replace(/_/g, ' ')}</span>
                    <span className="text-[10px] text-[#737373] font-mono truncate">{event.incidentId}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

      </main>
    </div>
  )
}
