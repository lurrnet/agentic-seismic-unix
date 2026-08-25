# INSTALL.md

These files are intended for the existing OpenClaw agent:

`oci-seismic`

OpenClaw's standard injected workspace files include:

- `AGENTS.md`
- `SOUL.md`
- `IDENTITY.md`
- `USER.md`
- optional `MEMORY.md`

`BOOTSTRAP.md` is intentionally not included because this is an existing prepared agent and OpenClaw treats it as a one-time first-run file.

## Install

Find the workspace for `oci-seismic`:

```bash
openclaw agents list
```

Back up the current policy files, then replace them with:

```text
AGENTS.md
SOUL.md
IDENTITY.md
USER.md
MEMORY.md
```

`HARDENING.md` is administrator documentation and does not need to be injected into the agent prompt.

## Validate

```bash
openclaw agents list --bindings
openclaw doctor
```

Then test from Agentic SeismicUnix and verify:

```text
Pinned Agent: oci-seismic
```

## Critical reminder

The Markdown files do not technically remove OpenClaw tools.

Apply the actual tool-policy restrictions described in `HARDENING.md`.
