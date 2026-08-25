# Security Model

Agentic SeismicUnix treats user chat, model output, and OpenClaw responses as untrusted input.

## OpenClaw boundary

The web application is pinned to the dedicated OpenClaw agent:

```text
oci-seismic
```

That agent should be configured with least privilege. It should not have shell/exec, SSH, Docker, filesystem, browser automation, generic host administration, or unrelated account-write tools. Seismic Unix execution remains inside this application through the YAML tool registry, parameter validator, and `subprocess.run(argv)` without `shell=True`.

## Network exposure

OpenClaw should remain bound to host loopback at `127.0.0.1:18789`. Streamlit is also configured to listen on `127.0.0.1:8501`; Internet access should terminate at Cloudflare Tunnel / Cloudflare Access rather than exposing port 8501 directly.

`network_mode: host` is intentionally retained in v0.9.1 because the OpenClaw Gateway currently listens only on host loopback. Removing host networking without first adding a dedicated bridge/proxy endpoint would break the OpenClaw connection. A future hardening step can replace host networking once a narrowly scoped container-reachable Gateway endpoint is available.

## Processing controls

Default limits:

- maximum upload: 2 GiB
- maximum project storage: 20 GiB
- maximum processing steps: 100
- maximum SU command runtime: 1800 seconds
- one concurrent SU processing job per application process

These defaults are configurable with:

```text
SECURITY_MAX_UPLOAD_BYTES
SECURITY_MAX_PROJECT_BYTES
SECURITY_MAX_PROCESSING_STEPS
SECURITY_SU_TIMEOUT_SECONDS
```

Before a processing step, the workflow reserves conservative disk headroom. Failed or timed-out SU output files are removed.

## Container controls

The production Compose service uses:

- read-only root filesystem
- writable `/data` bind mount only for projects
- tmpfs `/tmp` with `noexec,nosuid,nodev`
- `cap_drop: ALL`
- `no-new-privileges:true`
- PID limit
- Streamlit XSRF protection

## Audit trail

Security-related decisions are appended per project to:

```text
history/security_audit.jsonl
```

Events include successful processing, policy/validation rejection, execution failure, proposal rejection, and rejected explicit/follow-up authorization.

## Deployment recommendation

Place Cloudflare Access authentication in front of the Streamlit hostname and restrict access to authorized identities. Do not expose the OpenClaw Gateway or Streamlit port directly to the public Internet.
