import { AlertCircle, AlertTriangle, Info, Play, CheckCircle } from 'lucide-react'

export default function DiagnosisPanel({ incident, aiDecision, safetyCheck, execution, onStartExecution }) {
  const severity = incident?.status === 'resolved' ? 'RESOLVED' : 'CRITICAL';
  
  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E5] h-full flex flex-col rounded-lg overflow-hidden relative">
      <div className="p-4 border-b border-[#E5E5E5] bg-[#FAFAFA]/50">
        <h2 className="text-sm font-semibold text-[#171717] uppercase tracking-wider">Diagnosis Panel</h2>
      </div>
      
      <div className="p-4 space-y-6 flex-1 overflow-y-auto">
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-[#737373] uppercase tracking-wider flex items-center gap-1.5">
            {severity === 'RESOLVED' ? <CheckCircle className="w-4 h-4 text-success" /> : <AlertTriangle className="w-4 h-4 text-error" />}
            Status
          </h3>
          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-1 text-sm rounded border font-medium ${severity === 'RESOLVED' ? 'bg-success/10 text-success border-success/50' : 'bg-error/10 text-error border-error/50'}`}>
              {severity}
            </span>
          </div>
        </div>

        <div className="space-y-2">
          <h3 className="text-sm font-medium text-[#737373] uppercase tracking-wider flex items-center gap-1.5">
            <Info className="w-4 h-4 text-accent" />
            Root Cause Analysis
          </h3>
          <div className="bg-[#FAFAFA] rounded p-3 border border-[#E5E5E5] w-full min-h-[60px]">
            <p className="text-sm text-[#171717]">
              {!incident ? "Waiting for incident..." :
               !aiDecision ? "AI is analyzing the incident..." :
               aiDecision.analysis}
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <h3 className="text-sm font-medium text-[#737373] uppercase tracking-wider flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4 text-[#737373]" />
            Suggested Action
          </h3>
          <ul className="space-y-2">
            {!aiDecision ? (
              <li className="text-sm text-[#737373]">No actions generated yet.</li>
            ) : (
              <li className="bg-[#FAFAFA] rounded p-3 border border-[#E5E5E5] text-sm text-[#171717] flex flex-col gap-2">
                <div className="flex items-start gap-2">
                   <span className="text-accent mt-0.5 font-mono text-xs">&gt;</span>
                   <span className="font-mono text-xs font-semibold">{aiDecision.command}</span>
                </div>
                {safetyCheck && (
                   <div className={`text-xs mt-1 ${safetyCheck.allowed ? 'text-success' : 'text-error'}`}>
                     Safety Check: {safetyCheck.allowed ? 'PASSED ✅' : 'FAILED 🚫'} - {safetyCheck.reason}
                   </div>
                )}
              </li>
            )}
          </ul>
        </div>
      </div>
      
      {/* Execution Action Button */}
      {safetyCheck?.allowed && (!execution || execution.status === 'failed') && severity !== 'RESOLVED' && (
        <div className="p-4 border-t border-[#E5E5E5] bg-white">
          <button 
            onClick={onStartExecution}
            className="w-full flex items-center justify-center gap-2 bg-[#171717] hover:bg-[#262626] text-white py-2 px-4 rounded text-sm font-medium transition-colors"
          >
            <Play className="w-4 h-4" />
            Execute Command
          </button>
        </div>
      )}
    </div>
  )
}
