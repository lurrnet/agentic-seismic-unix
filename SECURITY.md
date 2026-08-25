# Security Model

Agentic SeismicUnix treats user chat, model output, uploaded data, retrieved SU documentation, and OpenClaw responses as untrusted input.

## OpenClaw boundary

The web application is pinned to the dedicated OpenClaw agent:

```text
oci-seismic
```

That agent should be configured with least privilege. It should not have shell/exec, SSH, Docker, filesystem, browser automation, generic host administration, or unrelated account-write tools. Seismic Unix execution remains inside this application through the YAML tool registry, parameter validator, and argv-based subprocess execution without `shell=True`.

The Markdown files under `openclaw/` are behavioral policy, not a substitute for the real OpenClaw tool policy. Production deployment should remove forbidden capabilities from `oci-seismic` itself.

## Network exposure

OpenClaw should remain bound to host loopback at `127.0.0.1:18789`. Streamlit is configured to listen on `127.0.0.1:8501`; Internet access should terminate at Cloudflare Tunnel and Cloudflare Access rather than exposing port 8501 directly.

`network_mode: host` is intentionally retained because the OpenClaw Gateway currently listens only on host loopback. Removing host networking without first adding a dedicated bridge/proxy endpoint would break the OpenClaw connection.

## Heavy-job controls

SEG-Y import and SU processing share one application-level heavy-job gate. Only one heavy seismic job can run per application process at a time; read-only inspection and normal agent reasoning remain available.

Both import and processing are timeout bounded. Failed or timed-out jobs remove partial output files. SEG-Y import also cleans its temporary `hfile` and `bfile` sidecars.

Default limits:

- maximum upload: 2 GiB
- maximum project storage: 20 GiB
- maximum processing steps: 100
- maximum SU command runtime: 1800 seconds
- maximum SEG-Y import runtime: 1800 seconds
- minimum filesystem free-space reserve: 5 GiB
- maximum agent requests per project: 20/minute

Configure with:

```text
SECURITY_MAX_UPLOAD_BYTES
SECURITY_MAX_PROJECT_BYTES
SECURITY_MAX_PROCESSING_STEPS
SECURITY_SU_TIMEOUT_SECONDS
SECURITY_IMPORT_TIMEOUT_SECONDS
SECURITY_MIN_FREE_BYTES
SECURITY_AGENT_REQUESTS_PER_MINUTE
```

Before import or processing, the application verifies both project quota and actual filesystem free-space headroom.

## Path containment

Every project uses a generated 32-character hexadecimal project id. Runtime project input/output paths are resolved and required to remain below that project's `/data/projects/<id>` workspace. Operation names used to construct output filenames are sanitized.

This is defense-in-depth against future path-traversal mistakes as additional tools are added.

## Project lifecycle

Failed imports remove the abandoned project workspace. Long-lived deployments can review stale projects using:

```bash
python scripts/project_cleanup.py --older-than-days 30
```

This is dry-run by default. Deletion requires the explicit `--delete` flag.

## Knowledge layer

Local SU documentation under `docs/sudoc` is read-only application reference material. Retrieval results are never execution authorization and cannot override tool schemas, validators, approval rules, or dataset evidence.

## Container controls

The production Compose service uses:

- read-only root filesystem
- writable `/data` bind mount only for projects
- tmpfs `/tmp` with `noexec,nosuid,nodev`
- `cap_drop: ALL`
- `no-new-privileges:true`
- PID limit
- Streamlit XSRF protection
- loopback-only Streamlit binding

## Audit trail

Security-related decisions are appended per project to:

```text
history/security_audit.jsonl
```

Audit records include timestamps, event category, project id, tool where relevant, duration/output size for successful processing, and rejection/failure reasons. Secrets and environment contents must never be written to this log.

## Test/release gate

GitHub Actions runs Python compile checks and pytest unit tests on pushes to `main` and pull requests. Unit tests cover path containment, project-id validation, explicit-command authorization boundaries, and deterministic SU knowledge retrieval. Runtime SU integration still requires the OCI/Docker deployment because GitHub-hosted CI does not install the full Seismic Unix runtime.

## Deployment requirement

Place Cloudflare Access authentication in front of the Streamlit hostname and restrict access to authorized identities. Do not expose the OpenClaw Gateway or Streamlit port directly to the public Internet.
