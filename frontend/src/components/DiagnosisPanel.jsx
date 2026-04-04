import { AlertCircle, AlertTriangle, Info, CheckCircle, ShieldAlert, ShieldCheck, Zap } from 'lucide-react'

const SEVERITY_STYLES = {
  critical: 'bg-red-50 text-red-700 border-red-200',
  high:     'bg-orange-50 text-orange-700 border-orange-200',
  medium:   'bg-yellow-50 text-yellow-700 border-yellow-200',
  low:      'bg-green-50 text-green-700 border-green-200',
}

export default function DiagnosisPanel({ incident, aiDecision, safetyCheck, execution }) {
  const isResolved = incident?.status === 'resolved'

  // analysis field is a JSON string packed by spacetime_tools.add_ai_decision
  let parsed = {}
  try { parsed = aiDecision?.analysis ? JSON.parse(aiDecision.analysis) : {} } catch {}
  
  const errorType  = parsed.error_type  || null
  const rootCause  = parsed.root_cause  || aiDecision?.command || null
  const severity   = parsed.severity    || (isResolved ? 'low' : 'critical')
  const numActions = parsed.num_actions ?? 0

  // ── DEBUG ──────────────────────────────────────────────────────────────────
  console.log('[DiagPanel] incident:', incident)
  console.log('[DiagPanel] aiDecision raw:', aiDecision)
  console.log('[DiagPanel] parsed:', parsed)
  console.log('[DiagPanel] errorType:', errorType, 'rootCause:', rootCause)
  // ──────────────────────────────────────────────────────────────────────────

  return (
    <div className="bg-white border border-[#E5E5E5] h-full flex flex-col rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#E5E5E5] bg-[#FAFAFA]">
        <h2 className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest">Diagnosis Panel</h2>
      </div>

      <div className="p-4 space-y-5 flex-1 overflow-y-auto">

        {/* STATUS */}
        <div className="space-y-2">
          <h3 className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest flex items-center gap-1.5">
            {isResolved
              ? <CheckCircle className="w-3.5 h-3.5 text-green-600" />
              : <AlertTriangle className="w-3.5 h-3.5 text-red-500" />}
            Status
          </h3>
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`px-2.5 py-1 text-xs rounded border font-bold uppercase tracking-widest ${isResolved ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-600 border-red-200'}`}>
              {isResolved ? 'Resolved' : 'Critical'}
            </span>
            {errorType && (
              <span className="px-2 py-1 text-[10px] rounded border font-mono bg-[#F5F5F5] text-[#737373] border-[#E5E5E5]">
                {errorType}
              </span>
            )}
            {severity && !isResolved && (
              <span className={`px-2 py-1 text-[10px] rounded border font-bold uppercase ${SEVERITY_STYLES[severity] || SEVERITY_STYLES.medium}`}>
                {severity}
              </span>
            )}
          </div>
        </div>

        {/* ROOT CAUSE */}
        <div className="space-y-2">
          <h3 className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-blue-500" />
            Root Cause Analysis
          </h3>
          <div className="bg-[#FAFAFA] rounded-lg p-3 border border-[#E5E5E5] min-h-[60px]">
            <p className="text-sm text-[#171717] leading-relaxed">
              {!incident
                ? 'Waiting for incident...'
                : !aiDecision
                ? 'AI is analyzing the incident...'
                : rootCause || 'Analysis complete.'}
            </p>
          </div>
        </div>

        {/* ACTIONS SUMMARY */}
        {aiDecision && (
          <div className="space-y-2">
            <h3 className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-[#737373]" />
              Suggested Actions
            </h3>
            <div className="bg-[#FAFAFA] rounded-lg p-3 border border-[#E5E5E5]">
              {numActions > 0 ? (
                <p className="text-sm text-[#171717]">
                  <span className="font-bold">{numActions}</span> action{numActions !== 1 ? 's' : ''} proposed by the AI agent.
                </p>
              ) : (
                <p className="text-sm text-[#737373]">No actions generated yet.</p>
              )}
            </div>
          </div>
        )}

        {/* SAFETY CHECK */}
        {safetyCheck && (
          <div className="space-y-2">
            <h3 className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest flex items-center gap-1.5">
              {safetyCheck.allowed
                ? <ShieldCheck className="w-3.5 h-3.5 text-green-600" />
                : <ShieldAlert className="w-3.5 h-3.5 text-red-500" />}
              Safety Check
            </h3>
            <div className={`rounded-lg p-3 border text-sm ${safetyCheck.allowed ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
              <span className="font-bold">{safetyCheck.allowed ? '✅ ALLOWED' : '🚫 BLOCKED'}</span>
              {safetyCheck.reason && (
                <p className="text-xs mt-1 opacity-80">{safetyCheck.reason}</p>
              )}
            </div>
          </div>
        )}

        {/* EXECUTION */}
        {execution && (
          <div className="space-y-2">
            <h3 className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-purple-500" />
              Execution
            </h3>
            <div className={`rounded-lg p-3 border text-sm font-mono ${execution.status === 'success' ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
              {execution.status?.toUpperCase()} — {execution.action}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
