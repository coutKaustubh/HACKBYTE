import { useState, useEffect, useRef } from 'react'

export default function Terminal({ incident, aiDecision, safetyCheck, execution, streamingLogs = [] }) {
  const [derivedLogs, setDerivedLogs] = useState([])
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [derivedLogs, streamingLogs])

  useEffect(() => {
    const computedLogs = []
    if (incident) {
      computedLogs.push({ type: 'error', text: `[ALERT] ${incident.service} service reported failure` })
      computedLogs.push({ type: 'normal', text: `[LOGS] ${incident.logs}` })
      
      if (!aiDecision) {
        computedLogs.push({ type: 'normal', text: `[AI] analyzing issue...` })
      } else {
        let analysisText = aiDecision.analysis;
        try {
          if (typeof analysisText === 'string' && analysisText.startsWith('{')) {
            const parsed = JSON.parse(analysisText);
            analysisText = parsed.root_cause || parsed.analysis || analysisText;
          }
        } catch (e) {}

        computedLogs.push({ type: 'normal', text: `[AI] Analysis complete: ${analysisText} (Confidence: ${aiDecision.confidence})` })
        
        if (!safetyCheck) {
          computedLogs.push({ type: 'normal', text: `[SAFE] validating proposed fix...` })
        } else {
          if (safetyCheck.allowed) {
            computedLogs.push({ type: 'success', text: `[SAFE] APPROVED ✅ (${safetyCheck.reason})` })
          } else {
            computedLogs.push({ type: 'error', text: `[SAFE] BLOCKED 🚫 (${safetyCheck.reason})` })
          }
          
          if (safetyCheck.allowed) {
            if (!execution) {
               computedLogs.push({ type: 'normal', text: `[SYSTEM] waiting for execution...` })
            } else {
               computedLogs.push({ type: 'normal', text: `[EXEC] running...` })
               if (execution.status === 'success') {
                 computedLogs.push({ type: 'success', text: `[EXEC] SUCCESS ✅` })
                 computedLogs.push({ type: 'normal', text: `[EXEC OUT] ${execution.output}` })
               } else if (execution.status === 'failed') {
                 computedLogs.push({ type: 'error', text: `[EXEC] FAILED ❌` })
                 computedLogs.push({ type: 'error', text: `[EXEC OUT] ${execution.output}` })
               }
            }
          }
        }
      }

      if (incident.status === 'resolved') {
        computedLogs.push({ type: 'success', text: `[SYSTEM] status set to RESOLVED. System nominal.` })
      }
    } else {
       computedLogs.push({ type: 'normal', text: `[SYSTEM] Tail connected. Listening for incidents...` })
    }
    setDerivedLogs(computedLogs)
  }, [incident, aiDecision, safetyCheck, execution])

  const displayLogs = streamingLogs.length > 0 ? streamingLogs : derivedLogs

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E5] h-full flex flex-col rounded-lg font-mono text-sm overflow-hidden shadow-lg">
      <div className="bg-[#FAFAFA] border-b border-[#E5E5E5] p-3 flex gap-2 items-center">
        <div className="w-3 h-3 rounded-full bg-red-400"></div>
        <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
        <div className="w-3 h-3 rounded-full bg-green-400"></div>
        <span className="ml-2 text-[#737373] text-xs font-bold">live_terminal // console</span>
      </div>
      <div className="p-4 overflow-y-auto flex-1 space-y-1.5 transition-all">
        {displayLogs.map((log, idx) => (
          <div 
            key={idx} 
            className={`
              whitespace-pre-wrap break-all
              ${log.type === 'error' ? 'text-red-500 font-bold' : ''}
              ${log.type === 'success' ? 'text-green-600 font-bold' : ''}
              ${log.type === 'ai' ? 'text-purple-600' : ''}
              ${log.type === 'token' ? 'text-[#171717]' : ''}
              ${log.type === 'system' ? 'text-[#737373] italic' : ''}
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
