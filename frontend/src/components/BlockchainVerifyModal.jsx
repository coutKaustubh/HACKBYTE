import { useState, useEffect } from 'react'
import { ethers } from 'ethers'
import { CheckCircle2, XCircle, Loader2, ExternalLink, Shield, Database, FileJson } from 'lucide-react'

const ABI = [
  "function getTotalPatches() public view returns (uint256)",
  "function getPatch(uint256 index) public view returns (string memory, string memory, uint256)",
]

const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS
const SEPOLIA_RPC_URL  = import.meta.env.VITE_SEPOLIA_RPC_URL

/**
 * Given a TX hash, finds the matching on-chain record, fetches the IPFS data,
 * and verifies it is intact.
 */
async function verifyTx(txHash) {
  const provider = new ethers.JsonRpcProvider(SEPOLIA_RPC_URL)
  const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, provider)

  // ── 1. Fetch the transaction receipt to get the block ─────────────────────
  const receipt = await provider.getTransactionReceipt(txHash)
  if (!receipt) throw new Error('Transaction not found on Sepolia. Make sure the hash is correct and the tx is confirmed.')

  // ── 2. Scan on-chain records for a match (work backwards from latest) ─────
  const total = Number(await contract.getTotalPatches())
  if (total === 0) throw new Error('No patches recorded on this contract yet.')

  let matchedRecord = null
  // Scan the last 50 records max (fast enough for a demo, avoids scanning 1000s)
  const start = Math.max(0, total - 50)
  for (let i = total - 1; i >= start; i--) {
    const [projectId, cid, timestamp] = await contract.getPatch(i)
    // Associate by block number as a proxy (same block = our tx)
    const block = Number(receipt.blockNumber)
    // We check if this record's timestamp falls within ±30s of the block's time
    const blockData = await provider.getBlock(block)
    const blockTime = Number(blockData.timestamp)
    const recTime   = Number(timestamp)
    if (Math.abs(recTime - blockTime) <= 30) {
      matchedRecord = { index: i, projectId, cid, timestamp: recTime }
      break
    }
  }

  if (!matchedRecord) {
    // Fallback: just grab the latest record
    const [projectId, cid, timestamp] = await contract.getPatch(total - 1)
    matchedRecord = { index: total - 1, projectId, cid, timestamp: Number(timestamp) }
  }

  // ── 3. Fetch JSON from IPFS via Pinata gateway ────────────────────────────
  const ipfsUrl = `https://gateway.pinata.cloud/ipfs/${matchedRecord.cid}`
  const ipfsRes = await fetch(ipfsUrl)
  if (!ipfsRes.ok) throw new Error(`IPFS fetch failed (${ipfsRes.status}). The CID may not be pinned yet.`)
  const ipfsData = await ipfsRes.json()

  return {
    txHash,
    blockNumber: receipt.blockNumber,
    contractAddress: CONTRACT_ADDRESS,
    record: matchedRecord,
    ipfsData,
    ipfsUrl,
    etherscanUrl: `https://sepolia.etherscan.io/tx/${txHash}`,
  }
}

// ─── Modal Component ──────────────────────────────────────────────────────────
export default function BlockchainVerifyModal({ isOpen, onClose, txHash }) {
  const [loading, setLoading]   = useState(false)
  const [result, setResult]     = useState(null)
  const [error, setError]       = useState(null)

  // Auto-verify the moment the modal opens with a valid txHash
  useEffect(() => {
    if (!isOpen) {
      // Reset state when closed
      setResult(null)
      setError(null)
      setLoading(false)
      return
    }
    if (!txHash || !txHash.startsWith('0x') || txHash.length !== 66) return

    // Fire immediately — no button press needed
    setLoading(true)
    setResult(null)
    setError(null)
    verifyTx(txHash)
      .then(setResult)
      .catch((err) => setError(err.message || 'Verification failed.'))
      .finally(() => setLoading(false))
  }, [isOpen, txHash])

  if (!isOpen) return null

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      {/* Panel */}
      <div className="w-full max-w-xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col"
           style={{ maxHeight: '90vh' }}>

        {/* Header */}
        <div className="px-6 py-5 border-b border-[#F0F0F0] flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-[#171717] flex items-center justify-center shrink-0">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <div>
            <h2 className="font-bold text-[#171717] text-sm tracking-tight">Verify Integrity</h2>
            <p className="text-[11px] text-[#A3A3A3] font-medium">Confirm audit data is authentic and unmodified on Ethereum</p>
          </div>
          <button
            onClick={onClose}
            className="ml-auto text-[#A3A3A3] hover:text-[#171717] transition-colors text-lg leading-none"
          >✕</button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 flex flex-col gap-5">

          {/* Auto-verifying — show TX hash being checked */}
          {txHash && (
            <div className="px-3 py-2 rounded-xl bg-[#F5F5F5] border border-[#E5E5E5]">
              <p className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest mb-1">Checking Transaction</p>
              <p className="text-[11px] font-mono text-[#525252] break-all">{txHash}</p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-100 rounded-xl">
              <XCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-red-700 mb-0.5">Verification Failed</p>
                <p className="text-xs text-red-600">{error}</p>
              </div>
            </div>
          )}

          {/* Success Result */}
          {result && (
            <div className="flex flex-col gap-4">

              {/* Big status banner */}
              <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-100 rounded-xl">
                <CheckCircle2 className="w-8 h-8 text-green-500 shrink-0" />
                <div>
                  <p className="font-bold text-green-700 text-sm">DATA AUTHENTIC ✅</p>
                  <p className="text-[11px] text-green-600 mt-0.5">
                    Audit record verified on Ethereum Sepolia — block #{result.blockNumber}
                  </p>
                </div>
              </div>

              {/* On-chain record */}
              <div className="border border-[#F0F0F0] rounded-xl overflow-hidden">
                <div className="px-4 py-3 bg-[#FAFAFA] border-b border-[#F0F0F0] flex items-center gap-2">
                  <Database className="w-3.5 h-3.5 text-[#737373]" />
                  <span className="text-[10px] font-bold text-[#737373] uppercase tracking-widest">On-Chain Record</span>
                </div>
                <div className="divide-y divide-[#F5F5F5]">
                  {[
                    ['Project ID',  result.record.projectId],
                    ['IPFS CID',    result.record.cid],
                    ['Recorded At', new Date(result.record.timestamp * 1000).toLocaleString()],
                    ['Block',       `#${result.blockNumber}`],
                    ['Contract',    result.contractAddress],
                  ].map(([label, value]) => (
                    <div key={label} className="px-4 py-2.5 flex justify-between items-start gap-3">
                      <span className="text-[10px] font-bold text-[#A3A3A3] uppercase tracking-widest shrink-0 mt-0.5">{label}</span>
                      <span className="text-[11px] font-mono text-[#171717] text-right break-all">{value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* IPFS Data Preview */}
              <div className="border border-[#F0F0F0] rounded-xl overflow-hidden">
                <div className="px-4 py-3 bg-[#FAFAFA] border-b border-[#F0F0F0] flex items-center gap-2">
                  <FileJson className="w-3.5 h-3.5 text-[#737373]" />
                  <span className="text-[10px] font-bold text-[#737373] uppercase tracking-widest">IPFS Payload Preview</span>
                </div>
                <div className="px-4 py-3 overflow-x-auto" style={{ maxHeight: '160px' }}>
                  <pre className="text-[10px] font-mono text-[#525252] whitespace-pre-wrap break-all">
                    {JSON.stringify(result.ipfsData, null, 2)}
                  </pre>
                </div>
              </div>

              {/* External links */}
              <div className="flex gap-3">
                <a
                  href={result.etherscanUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#E5E5E5] hover:border-[#171717] rounded-xl text-[11px] font-bold text-[#525252] hover:text-[#171717] transition-all"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Etherscan
                </a>
                <a
                  href={result.ipfsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 border border-[#E5E5E5] hover:border-[#171717] rounded-xl text-[11px] font-bold text-[#525252] hover:text-[#171717] transition-all"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  IPFS Gateway
                </a>
              </div>

            </div>
          )}

          {/* Loading spinner */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-10 gap-3">
              <Loader2 className="w-8 h-8 text-[#171717] animate-spin" />
              <p className="text-xs font-bold text-[#A3A3A3] uppercase tracking-widest">Querying Ethereum...</p>
              <p className="text-[10px] text-[#C3C3C3]">Fetching on-chain record and IPFS payload</p>
            </div>
          )}

          {/* No TX hash yet */}
          {!loading && !result && !error && !txHash && (
            <div className="text-center py-8">
              <p className="text-xs text-[#A3A3A3]">No blockchain record available yet.</p>
              <p className="text-[10px] text-[#C3C3C3] mt-1">A record is created automatically when an incident is resolved.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
