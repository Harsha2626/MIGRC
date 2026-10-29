# Local AI Assist Setup (Policy Evaluation)

MIGRC has one AI-assisted feature that is **local to your own machine only**:
AI-assisted policy evaluation (the "Evaluate" button on a policy's detail
page). It judges whether a policy's evidence is sufficient by talking to a
`compliance-auditor` agent running on a local [OpenCode](https://opencode.ai)
server - not a hosted API.

This is entirely optional. If you skip this setup, the feature fails open:
`evaluate_policy()` just returns `None` and the UI shows "Evaluation
unavailable" instead of erroring. Nothing else in MIGRC depends on it.

It is also **zero-config across developers by design** - the code never
hardcodes a username, an absolute path, or a specific person's machine. Every
developer who wants this feature working sets it up independently on their
own machine, pointing at their own local OpenCode server. See
`app/services/ai_opencode_policy_evaluation.py` for the implementation.

## What you need

| Requirement | Default | Where it's read |
|---|---|---|
| A running local OpenCode server | port `28894` | `OPENCODE_SERVER_URL` env var (optional - only set this if you changed the port) |
| `OPENCODE_SERVER_PASSWORD` env var | *(none - required)* | Basic Auth password MIGRC sends as `opencode:<password>` |
| A `compliance-auditor` agent config | `~/.config/opencode/agent/compliance-auditor.md` | Resolved by the OpenCode server itself, not by MIGRC - OpenCode looks this up by agent name whenever MIGRC creates a session with `"agent": "compliance-auditor"` |

Nothing above is machine-specific: `OPENCODE_SERVER_PASSWORD` is yours to
choose, the agent config path is under *your own* home directory (handled
entirely by OpenCode, via whatever home-directory resolution OpenCode itself
uses on your OS - MIGRC's Python code never constructs or reads this path),
and the port only needs to change if `28894` conflicts with something else on
your machine.

## Step-by-step

### 1. Install and start OpenCode

Install OpenCode per the instructions at https://opencode.ai for your OS (the
MIGRC repo doesn't vendor or pin a specific OpenCode version/installer - use
whatever the OpenCode project currently recommends, then confirm it works
with `opencode --version` or equivalent).

Start its server with HTTP Basic Auth enabled, choosing your own password.
MIGRC sends `Authorization: Basic base64(opencode:<your password>)` on every
request, so whatever password you start the server with is the value you'll
put in `OPENCODE_SERVER_PASSWORD` below. Run `opencode serve --help` (or
check the OpenCode docs for your installed version) for the exact flag that
sets the server password and port on your version - MIGRC only cares that
*some* OpenCode server ends up reachable at a known URL with that password,
not which flags you used to start it.

By default MIGRC expects it at `http://127.0.0.1:28894`. If you start it on a
different port, set `OPENCODE_SERVER_URL` accordingly (see step 3).

### 2. Create the `compliance-auditor` agent config

MIGRC pins every policy-evaluation session to an agent literally named
`compliance-auditor`, with write/edit/bash/webfetch tools turned off as
defense in depth (the evaluation prompt is fully self-contained, so the
agent never needs to touch your filesystem, run commands, or reach the
network). OpenCode resolves that agent by looking for a config file at:

- **Windows:** `%USERPROFILE%\.config\opencode\agent\compliance-auditor.md`
- **macOS/Linux:** `~/.config/opencode/agent/compliance-auditor.md`

There is no such file shipped in this repo today - a copy-pasteable example
is provided at
[`docs/opencode-agent-compliance-auditor.example.md`](./opencode-agent-compliance-auditor.example.md).
Copy it into place:

```powershell
# Windows (PowerShell)
New-Item -ItemType Directory -Force "$env:USERPROFILE\.config\opencode\agent" | Out-Null
Copy-Item "docs\opencode-agent-compliance-auditor.example.md" "$env:USERPROFILE\.config\opencode\agent\compliance-auditor.md"
```

```bash
# macOS/Linux
mkdir -p ~/.config/opencode/agent
cp docs/opencode-agent-compliance-auditor.example.md ~/.config/opencode/agent/compliance-auditor.md
```

The frontmatter fields in that example (`mode`, `tools.write`, `tools.edit`,
`tools.bash`, `tools.webfetch`, `tools.patch`) reflect what the MIGRC code
assumes the agent has turned off; the exact YAML schema OpenCode accepts can
change between OpenCode versions, so if your installed version rejects it,
check your OpenCode version's own agent-config docs and adjust the
frontmatter accordingly - the body prompt text doesn't need to change.

### 3. Set your environment variables

Add to your local `.env` (gitignored - never commit real secrets here):

```
OPENCODE_SERVER_PASSWORD=<the password you started OpenCode's server with>
# Only needed if you changed the port/host in step 1:
# OPENCODE_SERVER_URL=http://127.0.0.1:28894
```

### 4. Verify it's working

Start MIGRC (`python app.py`) and open the **Setup Wizard** - the "Enable
AI-Assisted Policy Evaluation" task under Compliance Setup does a live
reachability check against your local OpenCode server and shows:

- **AI Assist: Connected** - a server answered; the feature is live.
- **AI Assist: Not Running** - `OPENCODE_SERVER_PASSWORD` is set but no
  server responded (check it's actually started, on the right port, with
  the matching password).
- **AI Assist: Not Configured** - `OPENCODE_SERVER_PASSWORD` isn't set yet.

Then open any policy and click **Evaluate** to run a real evaluation.

## Notes on shared state

- **Sessions are not persisted or shared.** Every evaluation call creates a
  brand-new OpenCode session in a throwaway scratch directory and deletes it
  when done (see `evaluate_policy()` in
  `app/services/ai_opencode_policy_evaluation.py`). No session id is ever
  written to the database or to disk, so there's nothing from one
  developer's machine that could leak into another's.
- **`AiAuditorLock` (the DB table) is scoped per machine, even when the
  database itself is shared.** MIGRC's dev `DATABASE_URL` can point at (and in
  practice does point at) a single Postgres instance shared across several
  developers' machines, while each developer's OpenCode server is still local
  to their own machine. Each machine locks its own row (keyed by a hash of its
  hostname, stored in `machine_id`), so this just serializes concurrent
  requests within *your own* app process against *your own* OpenCode server -
  it never blocks another developer's idle server. See the docstring on
  `AiAuditorLock` in `app/models.py` and `_machine_lock_id()` in
  `app/services/ai_opencode_policy_evaluation.py` for details.
