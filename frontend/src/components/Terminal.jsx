import { useState, useEffect, useRef } from 'react'

export default function Terminal({ incident, aiDecision, safetyCheck, execution }) {
  const [logs, setLogs] = useState([])
  const bottomRef = useRef(null)

  useEffect(() => {
    // Scroll to bottom whenever logs update
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // Derive logs from real-time state transitions
  useEffect(() => {
    const computedLogs = [];

    if (incident) {
      computedLogs.push({ type: 'error', text: `[ALERT] ${incident.service} service reported failure` });
      computedLogs.push({ type: 'normal', text: `[LOGS] ${incident.logs}` });
      
      if (!aiDecision) {
        computedLogs.push({ type: 'normal', text: `[AI] analyzing issue...` });
      } else {
        computedLogs.push({ type: 'normal', text: `[AI] Analysis complete: ${aiDecision.analysis} (Confidence: ${aiDecision.confidence})` });
        
        if (!safetyCheck) {
          computedLogs.push({ type: 'normal', text: `[SAFE] validating proposed fix...` });
        } else {
          if (safetyCheck.allowed) {
            computedLogs.push({ type: 'success', text: `[SAFE] APPROVED ✅ (${safetyCheck.reason})` });
          } else {
            computedLogs.push({ type: 'error', text: `[SAFE] BLOCKED 🚫 (${safetyCheck.reason})` });
          }
          
          if (safetyCheck.allowed) {
            if (!execution) {
               computedLogs.push({ type: 'normal', text: `[SYSTEM] waiting for user execution...` });
            } else {
               computedLogs.push({ type: 'normal', text: `[EXEC] running...` });
               if (execution.status === 'success') {
                 computedLogs.push({ type: 'success', text: `[EXEC] SUCCESS ✅` });
                 computedLogs.push({ type: 'normal', text: `[EXEC OUT] ${execution.output}` });
               } else if (execution.status === 'failed') {
                 computedLogs.push({ type: 'error', text: `[EXEC] FAILED ❌` });
                 computedLogs.push({ type: 'error', text: `[EXEC OUT] ${execution.output}` });
               }
            }
          }
        }
      }

      if (incident.status === 'resolved') {
        computedLogs.push({ type: 'success', text: `[SYSTEM] status set to RESOLVED. System nominal.` });
      } else if (incident.status === 'error') {
        computedLogs.push({ type: 'error', text: `[SYSTEM] status set to ERROR. Operator attention required.` });
      }
    } else {
       computedLogs.push({ type: 'normal', text: `[SYSTEM] Tail connected. Listening for incidents...` });
    }

    setLogs(computedLogs);
  }, [incident, aiDecision, safetyCheck, execution]);

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E5] h-full flex flex-col rounded-lg font-mono text-sm overflow-hidden shadow-lg">
      <div className="bg-[#FAFAFA] border-b border-[#E5E5E5] p-3 flex gap-2 items-center">
        <div className="w-3 h-3 rounded-full bg-error/50"></div>
        <div className="w-3 h-3 rounded-full border border-[#A3A3A3]/30"></div>
        <div className="w-3 h-3 rounded-full border border-[#A3A3A3]/30"></div>
        <span className="ml-2 text-[#737373] text-xs">live_terminal // console</span>
      </div>
      <div className="p-4 overflow-y-auto flex-1 space-y-1.5 transition-all">
        {logs.map((log, idx) => (
          <div 
            key={idx} 
            className={`
              ${log.type === 'error' ? 'text-error' : ''}
              ${log.type === 'success' ? 'text-success' : ''}
              ${log.type === 'normal' ? 'text-[#171717]' : ''}
            `}
          >
            {log.text}
          </div>
        ))}
        <div ref={bottomRef} className="h-1" />
      </div>
    </div>
  )
}
