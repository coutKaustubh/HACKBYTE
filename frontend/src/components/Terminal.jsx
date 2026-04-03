import { useState, useEffect, useRef } from 'react'

const mockData = {
  incident: { id: 1, service: "nginx", status: "error", logs: "connection refused" },
  ai_decision: { analysis: "memory issue", command: "restart service", confidence: 0.91 },
  safety_check: { allowed: false, reason: "unsafe command" },
  execution: { status: "failed", output: "restart failed" }
};

export default function Terminal() {
  const [logs, setLogs] = useState([])
  const bottomRef = useRef(null)

  useEffect(() => {
    // Scroll to bottom whenever logs update
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  useEffect(() => {
    let currentStep = 0;
    
    // Simulate real-time updates based on requirement
    const steps = [
      () => setLogs(prev => [...prev, { type: 'error', text: `[ALERT] ${mockData.incident.service} service failed` }]),
      () => setLogs(prev => [...prev, { type: 'normal', text: `[AI] analyzing issue...` }]),
      () => setLogs(prev => [...prev, { type: 'normal', text: `[AI] ${mockData.ai_decision.analysis} detected (confidence: ${mockData.ai_decision.confidence})` }]),
      () => setLogs(prev => [...prev, { type: 'error', text: `[SAFE] BLOCKED 🚫 (${mockData.safety_check.reason})` }]),
      () => setLogs(prev => [...prev, { type: 'normal', text: `[EXEC] running...` }]),
      () => setLogs(prev => [...prev, { type: 'error', text: `[EXEC] ${mockData.execution.status} ❌` }]),
      () => setLogs(prev => [...prev, { type: 'normal', text: `[SYSTEM] incident not resolved` }]),
    ];

    const timer = setInterval(() => {
      if (currentStep < steps.length) {
        steps[currentStep]();
        currentStep++;
      } else {
        clearInterval(timer); // stop once all steps run
      }
    }, 1000); // 1 log per second

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E5] h-full flex flex-col rounded-lg font-mono text-sm overflow-hidden shadow-lg">
      <div className="bg-[#FAFAFA] border-b border-[#E5E5E5] p-3 flex gap-2 items-center">
        <div className="w-3 h-3 rounded-full bg-error/50"></div>
        <div className="w-3 h-3 rounded-full border border-[#A3A3A3]/30"></div>
        <div className="w-3 h-3 rounded-full border border-[#A3A3A3]/30"></div>
        <span className="ml-2 text-[#737373] text-xs">live_terminal // console</span>
      </div>
      <div className="p-4 overflow-y-auto flex-1 space-y-1.5">
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
