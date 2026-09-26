# BECP Engineering Workstation Terminal Requirements

## Purpose
The Engineering Workstation Terminal is BECP's privileged full-computer engineering interface.
It exists in addition to application agents and normal capability-based controls.
Its purpose is to let an authorized Blackmore engineer, NIKI, or approved AI engineering client work on an enrolled engineering computer when app-level capabilities are insufficient.

## Primary BTG implementation
The first designated engineering workstation is `BTG`.
The terminal is bound to the enrolled workstation identity and must reject execution on a different device identity.
The initial working root is `<LOCAL_DRIVE>/Blackmore_Technology_Group`, but privileged terminal sessions are not restricted to that directory.
Full-computer scope means all local filesystems, drives, executables, developer tools, and resources that the BECP service account is permitted to access by Windows.
BECP does not bypass Windows ACLs, UAC, credential boundaries, BitLocker, or other operating-system security controls.

## Required terminal functions
BECP shall create and close privileged terminal sessions.
BECP shall execute PowerShell and Windows Command Processor commands.
BECP shall support additional explicitly enabled shells such as PowerShell 7.
BECP shall allow the terminal working directory to be changed to any filesystem location available to the service account.
BECP shall enumerate available local drives.
BECP shall capture stdout, stderr, return code, duration, timeout state, and output truncation state.
BECP shall support configurable command timeouts and output limits.

## Privilege separation
The full-workstation terminal is a distinct BECP privilege domain.
HUNTAR, HIKEAR, SEARCHAR, field devices, and ordinary application agents must never inherit this access.
Normal `chatgpt_engineer` and `niki_engineer` identities are insufficient for workstation-terminal execution.
Only explicitly privileged identities such as `chatgpt_privileged_engineer`, `niki_privileged_engineer`, or `blackmore_admin` may be eligible.
Privileged terminal capabilities are classified at BECP's highest normal engineering risk level.
An explicit approval reference is required before terminal operations are accepted by policy.
The production authentication service must cryptographically bind the authenticated client identity to the authorized role; role names supplied by an untrusted caller must never be trusted by themselves.

## Audit and evidence
Session creation, working-directory changes, command execution, completion, and session closure shall be audited.
Audit events shall identify actor, role where available, target device, session, time, command digest, sanitized command preview, outcome, and correlation information.
Known credential-like values in command previews shall be redacted.
The BECP hash-chained audit log shall cover terminal actions.

## AI engineering use
ChatGPT access shall be provided through the BECP gateway/MCP adapter, not by exposing a raw network shell directly to ChatGPT.
NIKI shall use the same BECP authorization path for privileged workstation access.
The AI client may use the terminal for repository inspection, script creation, builds, tests, diagnostics, dependency work, repair, deployment preparation, and other authorized engineering tasks.
Structured BECP capabilities remain preferred when an equivalent safe operation exists; the workstation terminal is the privileged engineering escape hatch for tasks that require general computer access.

## Multi-workstation fleet requirement
`BTG` is the first BECP Engineering Workstation, not a special hard-coded endpoint.
Any Blackmore-issued or approved engineering laptop, desktop, build workstation, or server may be enrolled and assigned a persistent BECP device ID, human-readable alias, owner/assignee, device role, certificate identity, capability set, and revocation state.
The workstation terminal shall operate against the Windows account or service security token running the local BECP agent.
Therefore two engineering laptops may legitimately have different filesystem, administrator, network-share, SDK, signing, repository, or deployment permissions.
BECP must report those effective privileges rather than pretending all enrolled workstations are equivalent.
Administrator elevation remains governed by Windows/UAC or an explicitly provisioned privileged service identity.

## Persistent device identity and discovery
Every enrolled engineering workstation shall appear in the BECP Device Registry.
The registry shall retain device ID, alias, hostname, assigned engineer, platform, agent version, online state, last-seen time, terminal availability, capabilities, certificate identity, tags, and revocation state.
Agents shall normally establish an outbound authenticated connection to the BECP control plane and maintain a heartbeat/presence record.
AI clients shall discover authorized devices from the registry instead of depending on remembered hostnames or hard-coded machine names.
A revoked or unauthorized device shall not be returned to an AI client as an available engineering target.

## AI/GPT session identity
Every new ChatGPT, GPT, NIKI, API, or other AI engineering interaction shall receive a short-lived BECP AI session identity after authentication.
The AI session identity is separate from the persistent device identity.
The session record shall identify client type, authenticated principal, organization/workspace subject, issue time, expiry time, permitted device IDs, selected device ID, and correlation metadata.
A new chat shall never obtain workstation access merely because it knows a device name or prior session ID.
The BECP authentication layer must derive authorization from the authenticated client and server-side policy, not role names supplied by the model or prompt.
## New-chat connection bootstrap
On a new authorized AI session, BECP shall support a bootstrap flow equivalent to:
`session.bootstrap` -> authenticate caller and create ephemeral AI session.
`devices.list` -> return only devices the caller may see.
`device.describe` -> return the selected device's online state and exposed capabilities.
`device.select` -> bind the AI session to one authorized target.
`engineering.terminal.start` -> request privileged workstation terminal access when policy permits.
Subsequent operations shall carry AI session ID, authenticated actor identity, target device ID, capability, correlation ID, and any required approval reference.

## GPT / MCP integration
The ChatGPT-facing integration shall be implemented as a BECP MCP/App gateway that exposes discovery and action tools rather than a raw shell endpoint.
The connected BECP app is what allows a new ChatGPT conversation to know that enrolled Blackmore devices exist.
When invoked, ChatGPT queries the BECP registry through tools; device knowledge does not need to be stored in the conversation itself.
The gateway must support authenticated user/workspace identity and map that identity to BECP policy before returning device inventory or permitting actions.
The same discovery contract shall be reusable by NIKI and non-OpenAI clients through BECP's API.

## Example fleet
A fleet may contain `BTG`, `ENG-SHAWN-01`, `ENG-DEVELOPER-02`, `BUILD-WIN-01`, or any other enrolled workstation.
Names are human-readable aliases only; authorization shall bind to the persistent BECP device identity and certificate, not to the alias alone.
A newly hired software engineer can receive a laptop with the BECP Engineering Workstation Agent installed, enroll it, authenticate it, and then work with Blackmore applications through that machine according to the engineer's assigned permissions.
