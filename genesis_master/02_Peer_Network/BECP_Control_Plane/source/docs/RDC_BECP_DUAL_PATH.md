# Remote Desktop Commander + BECP Dual-Path Integration

## Purpose

BECP does not replace Remote Desktop Commander (RDC). RDC retains its existing direct filesystem, terminal, and PowerShell capabilities. BECP adds a second explicit route for operations that should pass through Blackmore engineering policy, device identity, approval, terminal ownership, and audit controls.

## Path A — Direct RDC

`ChatGPT Plus -> Remote Desktop Commander -> Windows / PowerShell / filesystem`

Use this path when direct computer administration is intentionally required. BECP does not intercept, disable, or alter this path.

## Path B — RDC via BECP

`ChatGPT Plus -> Remote Desktop Commander -> RDC_BECP_BRIDGE -> BECP Gateway -> BTG Agent -> Windows`

Use this path when the action should be governed and recorded by BECP.

## Bridge identity

The bridge authenticates as `remote-desktop-commander-becp-bridge` with subject `Remote Desktop Commander via BECP`. It is scoped to the enrolled BTG workstation and the capabilities listed in `config/RDC_BECP_BRIDGE.json`.
## Operator entry point

PowerShell wrapper:

`scripts\RDC_BECP_BRIDGE.ps1`

Supported operations:

- `status` — verify the BECP gateway.
- `devices` — discover BECP devices allowed to the bridge.
- `health` — route `system.health` through BECP.
- `action` — route an explicit BECP capability with JSON parameters.
- `terminal-run` — open an approved BECP engineering terminal, optionally set cwd, execute one command/batch, and close the terminal.

The wrapper prefers the compiled bridge executable when present and falls back to the installed/source Python module.

## Security behavior

Bridge bearer tokens are minted locally with short TTL and are never placed on the command line. Privileged BECP capabilities still require scoped one-time approval tokens. BECP's gateway and workstation-agent audit chains identify the bridge actor separately from direct RDC activity.

## Design rule

A ChatGPT/RDC workflow must choose the route explicitly. The presence of the BECP bridge must never silently disable or redirect normal Remote Desktop Commander operations.
