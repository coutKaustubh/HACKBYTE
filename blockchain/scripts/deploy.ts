import hre from "hardhat";
import "@nomicfoundation/hardhat-ethers";

async function main() {
  const connection = await hre.network.connect();
  const { ethers } = connection;

  const Contract = await ethers.getContractFactory("XOneAuditPatch");
  const contract = await Contract.deploy();
  await contract.waitForDeployment();
  console.log("Contract deployed to:", await contract.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});