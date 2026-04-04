import { ethers } from 'ethers';

// ─── Contract ABI (only what we need) ────────────────────────────────────────
const ABI = [
  "function logPatch(string memory _projectId, string memory _cid) public",
  "function getTotalPatches() public view returns (uint256)",
  "function getPatch(uint256 index) public view returns (string memory, string memory, uint256)",
  "event PatchLogged(string projectId, string cid, uint256 timestamp)",
];

// ─── Config from Vite env vars ────────────────────────────────────────────────
const PRIVATE_KEY      = import.meta.env.VITE_PRIVATE_KEY;
const SEPOLIA_RPC_URL  = import.meta.env.VITE_SEPOLIA_RPC_URL;
const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS;
const PINATA_API_KEY   = import.meta.env.VITE_PINATA_API_KEY;
const PINATA_SECRET    = import.meta.env.VITE_PINATA_SECRET_KEY;

/**
 * Uploads patchData to IPFS via Pinata, then stores the CID + projectId
 * on the XOneAuditPatch smart contract on Sepolia.
 *
 * @param {string} projectId  - Project ID string (e.g. "1" or "xone-project-001")
 * @param {object} patchData  - Arbitrary JSON object describing the patch/incident
 * @returns {{ cid: string, txHash: string }} CID and transaction hash
 */
export async function logToBlockchain(projectId, patchData) {
  // ── 1. Upload to IPFS via Pinata ─────────────────────────────────────────
  console.log('📦 Uploading to IPFS...');

  const pinataRes = await fetch('https://api.pinata.cloud/pinning/pinJSONToIPFS', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'pinata_api_key': PINATA_API_KEY,
      'pinata_secret_api_key': PINATA_SECRET,
    },
    body: JSON.stringify({
      pinataContent: patchData,
      pinataMetadata: {
        name: `XOne-Patch-${projectId}-${Date.now()}`,
      },
      pinataOptions: { cidVersion: 1 },
    }),
  });

  if (!pinataRes.ok) {
    const err = await pinataRes.text();
    throw new Error(`Pinata upload failed: ${err}`);
  }

  const { IpfsHash: cid } = await pinataRes.json();
  console.log('✅ IPFS CID:', cid);
  console.log('   View: https://gateway.pinata.cloud/ipfs/' + cid);

  // ── 2. Connect to Sepolia via ethers ─────────────────────────────────────
  const provider = new ethers.JsonRpcProvider(SEPOLIA_RPC_URL);
  const wallet   = new ethers.Wallet(PRIVATE_KEY, provider);
  const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, wallet);

  // ── 3. Store CID on-chain ─────────────────────────────────────────────────
  console.log('⛓️  Sending transaction to Sepolia...');
  const tx = await contract.logPatch(String(projectId), cid);
  console.log('⏳ TX submitted:', tx.hash);

  const receipt = await tx.wait();
  console.log('✅ Stored on blockchain! TX:', tx.hash);
  console.log('   Block:', receipt.blockNumber);
  console.log('   Etherscan: https://sepolia.etherscan.io/tx/' + tx.hash);

  return { cid, txHash: tx.hash };
}
