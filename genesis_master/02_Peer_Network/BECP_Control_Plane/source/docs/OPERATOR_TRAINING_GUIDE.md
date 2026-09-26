# BECP 0.2.1 Operator Training Guide

## Training Objective
An authorized operator must be able to start, verify, use, stop and recover BECP without bypassing its security model or confusing direct Remote Desktop Commander access with the governed BECP bridge path.

## Required Knowledge
The operator must understand the three production ports, the BTG enrolled device identity, the difference between client bearer identity and device mTLS identity, scoped approvals, terminal-session ownership, the kill switch, audit evidence and rollback boundaries.

## Exercise 1 - Startup and Health
Start the production Gateway and Agent using the controlled launchers.
Pass criteria: API health is `ok=true`; exactly one BTG workstation is online; registry agent version is 0.2.1; ports 8765-8767 are owned by the expected gateway process.

## Exercise 2 - Governed Read Operation
Use the RDC bridge or an authorized client to select BTG and run `system.health`.
Pass criteria: hostname is BTG, result is successful and the gateway/agent audit logs contain the routed request.

## Exercise 3 - Privileged Terminal
Obtain a fresh scoped approval, open a BECP engineering terminal, execute a harmless marker command and close the terminal.
Pass criteria: return code 0, expected marker returned, terminal owner matches the AI session and the approval cannot be replayed.

## Exercise 4 - Security Boundary
Attempt a file read outside the configured authorized roots.
Pass criteria: BECP returns `ok=false` with `path outside authorized roots`; no file content is returned.
## Exercise 5 - Kill Switch and Recovery
Disable remote access for BTG through the authorized administrator endpoint.
Pass criteria: the agent disconnects, routed actions are blocked, re-enabling remote access permits authenticated reconnection, and health succeeds after recovery.

## Exercise 6 - Dual RDC Paths
Run one harmless direct RDC PowerShell marker and one harmless BECP bridge terminal marker.
Pass criteria: both succeed; the BECP-routed command is distinctly attributable to `Remote Desktop Commander via BECP` in audit evidence.

## Exercise 7 - Service Recovery
With the agent in reconnect mode, stop and restart the gateway; then separately stop and restart the agent.
Pass criteria: both scenarios recover to one authenticated BTG device without modifying PKI or registry identity.

## Exercise 8 - MCP
Initialize MCP v2, enumerate the eight BECP tools, bootstrap a session, select BTG, run health and close the session.
Pass criteria: eight expected tools, successful health and successful session closure.

## Qualification of an Operator
An operator is considered trained only after completing all exercises without bypassing policy, exposing secret material, changing unrelated software or leaving ambiguous duplicate BECP production processes.
Training evidence should record operator, date, BECP version and exercise result; credentials or private-key contents must never be included.
