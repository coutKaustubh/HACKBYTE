import { ethers } from "ethers";
import { createRequire } from "module";
import * as dotenv from "dotenv";

dotenv.config();

// Use createRequire for @pinata/sdk since it's a CJS package with broken ESM type declarations
const require = createRequire(import.meta.url);
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const PinataSDK: any = require("@pinata/sdk");

// ─── Config ──────────────────────────────────────────────────────────────────
const {
  PRIVATE_KEY,
  SEPOLIA_RPC_URL,
  CONTRACT_ADDRESS,
  PINATA_API_KEY,
  PINATA_SECRET_KEY,
} = process.env;

if (!PRIVATE_KEY || !SEPOLIA_RPC_URL || !CONTRACT_ADDRESS || !PINATA_API_KEY || !PINATA_SECRET_KEY) {
  throw new Error("❌ Missing required env vars. Check PRIVATE_KEY, SEPOLIA_RPC_URL, CONTRACT_ADDRESS, PINATA_API_KEY, PINATA_SECRET_KEY in .env");
}

// ─── ABI (only the functions we need) ────────────────────────────────────────
const ABI = [
  "function logPatch(string memory _projectId, string memory _cid) public",
  "function getTotalPatches() public view returns (uint256)",
  "function getPatch(uint256 index) public view returns (string memory, string memory, uint256)",
  "event PatchLogged(string projectId, string cid, uint256 timestamp)",
];

// ─── The patch data to log ────────────────────────────────────────────────────
// Replace this with real data from teammates, or pass it in via CLI args
const patchData = {
  projectId: "xone-demo-001",
  patchVersion: "v1.0.0",
  patchedBy: "XOne AI Audit",
  timestamp: new Date().toISOString(),
  vulnerabilities: [
    {
      id: "VULN-001",
      type: "Reentrancy",
      severity: "CRITICAL",
      location: "contracts/Vault.sol:L42",
      description: "Reentrancy vulnerability in withdraw function",
      patched: true,
    },
    {
      id: "VULN-002",
      type: "Integer Overflow",
      severity: "HIGH",
      location: "contracts/Token.sol:L89",
      description: "Unchecked arithmetic in balance calculation",
      patched: true,
    },
  ],
  patchHash: "0xabcdef1234567890", // would be real hash in production
  status: "PATCH_SUCCESSFUL",
};

// ─── Main ─────────────────────────────────────────────────────────────────────
async function main() {
  console.log("🚀 Starting XOne Patch Logging...\n");

  // 1. Upload to IPFS via Pinata
  console.log("📦 Uploading patch data to IPFS via Pinata...");
  const pinata = new PinataSDK(PINATA_API_KEY!, PINATA_SECRET_KEY!);

  // Verify Pinata auth works
  await pinata.testAuthentication();
  console.log("✅ Pinata authenticated\n");

  const pinataResult = await pinata.pinJSONToIPFS(patchData, {
    pinataMetadata: {
      name: `XOne-Patch-${patchData.projectId}-${Date.now()}`,
    },
    pinataOptions: {
      cidVersion: 1,
    },
  });

  const cid = pinataResult.IpfsHash;
  console.log(`✅ Uploaded to IPFS!`);
  console.log(`   CID:     ${cid}`);
  console.log(`   URL:     https://gateway.pinata.cloud/ipfs/${cid}\n`);

  // 2. Connect to Sepolia via ethers
  console.log("🔗 Connecting to Sepolia...");
  const provider = new ethers.JsonRpcProvider(SEPOLIA_RPC_URL!);
  const wallet = new ethers.Wallet(PRIVATE_KEY!, provider);
  const network = await provider.getNetwork();
  console.log(`✅ Connected to network: ${network.name} (chainId: ${network.chainId})`);
  console.log(`   Wallet:  ${wallet.address}\n`);

  // 3. Interact with deployed contract
  console.log(`📝 Logging patch on-chain...`);
  console.log(`   Contract: ${CONTRACT_ADDRESS}\n`);

  const contract = new ethers.Contract(CONTRACT_ADDRESS!, ABI, wallet);

  const tx = await contract.logPatch(patchData.projectId, cid);
  console.log(`⏳ Transaction submitted: ${tx.hash}`);
  console.log(`   Track on Etherscan: https://sepolia.etherscan.io/tx/${tx.hash}\n`);

  const receipt = await tx.wait();
  console.log(`✅ Transaction confirmed in block ${receipt.blockNumber}!`);

  // 4. Verify it was stored
  const totalPatches = await contract.getTotalPatches();
  const lastIndex = Number(totalPatches) - 1;
  const [storedProjectId, storedCid, storedTimestamp] = await contract.getPatch(lastIndex);

  console.log(`\n📊 Verified on-chain record:`);
  console.log(`   Project ID:  ${storedProjectId}`);
  console.log(`   CID:         ${storedCid}`);
  console.log(`   Timestamp:   ${new Date(Number(storedTimestamp) * 1000).toISOString()}`);
  console.log(`   Total logs:  ${totalPatches.toString()}`);
  console.log(`\n🎉 Done! Patch permanently recorded on Sepolia Ethereum.`);
  console.log(`\n🔍 View patch data: https://gateway.pinata.cloud/ipfs/${cid}`);
  console.log(`🔍 View transaction: https://sepolia.etherscan.io/tx/${tx.hash}`);
  console.log(`🔍 View contract:    https://sepolia.etherscan.io/address/${CONTRACT_ADDRESS}`);
}

main().catch((error) => {
  console.error("❌ Error:", error.message);
  process.exit(1);
});
