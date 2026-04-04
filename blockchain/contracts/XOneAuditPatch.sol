
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract XOneAuditPatch {
    struct PatchRecord {
        string projectId;
        string cid;
        uint256 timestamp;
    }

    PatchRecord[] public patches;

    event PatchLogged(string projectId, string cid, uint256 timestamp);

    function logPatch(string memory _projectId, string memory _cid) public {
        patches.push(PatchRecord(_projectId, _cid, block.timestamp));
        emit PatchLogged(_projectId, _cid, block.timestamp);
    }

    function getPatch(uint256 index) public view returns (string memory, string memory, uint256) {
        PatchRecord memory p = patches[index];
        return (p.projectId, p.cid, p.timestamp);
    }

    function getTotalPatches() public view returns (uint256) {
        return patches.length;
    }
}