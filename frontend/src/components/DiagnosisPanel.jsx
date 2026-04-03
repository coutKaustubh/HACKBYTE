import { AlertCircle, AlertTriangle, Info } from 'lucide-react'

export default function DiagnosisPanel() {
  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E5] h-full flex flex-col rounded-lg overflow-hidden">
      <div className="p-4 border-b border-[#E5E5E5] bg-[#FAFAFA]/50">
        <h2 className="text-sm font-semibold text-[#171717] uppercase tracking-wider">Diagnosis Panel</h2>
      </div>
      
      <div className="p-4 space-y-6 flex-1 overflow-y-auto">
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-[#737373] uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-error" />
            Severity
          </h3>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 text-sm rounded bg-error/10 text-error border border-error/50 font-medium">
              CRITICAL
            </span>
          </div>
        </div>

        <div className="space-y-2">
          <h3 className="text-sm font-medium text-[#737373] uppercase tracking-wider flex items-center gap-1.5">
            <Info className="w-4 h-4 text-accent" />
            Root Cause
          </h3>
          <div className="bg-[#FAFAFA] rounded p-3 border border-[#E5E5E5] w-full">
            <p className="text-sm text-[#171717]">
              Memory issue detected (OOM condition) for service: nginx. Connection refused.
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <h3 className="text-sm font-medium text-[#737373] uppercase tracking-wider flex items-center gap-1.5">
            <AlertCircle className="w-4 h-4 text-[#737373]" />
            Suggested Actions
          </h3>
          <ul className="space-y-2">
            {[
              "Increase memory allocation for nginx",
              "Review error logs for memory leaks",
              "Setup memory usage alerts",
            ].map((action, idx) => (
              <li key={idx} className="bg-[#FAFAFA] rounded p-3 border border-[#E5E5E5] text-sm text-[#171717] flex items-start gap-2">
                <span className="text-[#737373] mt-0.5">•</span>
                <span>{action}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
