# Seismic Agent V0.3.3

V0.3.3 builds on V0.3 and adds a **dual-provider agent runtime**. The default deployment uses a local OpenClaw Gateway; direct OpenAI Responses API access remains available as an explicit deployment option. The deterministic Seismic Unix execution path and human approval gate are unchanged.

## What V0.3.3 adds

The new Chat Agent can use four structured tools:

```text
inspect_dataset        automatic / read-only
inspect_frequency      automatic / read-only
compare_datasets       automatic / read-only
apply_bandpass_filter  approval-gated
```

The important safety boundary is:

```text
LLM calls apply_bandpass_filter
        ↓
creates pending proposal only
        ↓
user clicks Approve & Run sufilter
        ↓
Workflow Engine
        ↓
Validator
        ↓
SU Executor
        ↓
sufilter
```

The model never gets arbitrary shell access and never directly executes Seismic Unix processing commands.

## Architecture

```text
Browser
   │
   ▼
Streamlit
   │
   ├──────────── Manual Process / QC tabs
   │
   ▼
SeismicAgent
   │
   ├── inspect_dataset
   ├── inspect_frequency
   ├── compare_datasets
   └── apply_bandpass_filter → pending approval only
                                  │
                                  ▼
                            Human approval
                                  │
                                  ▼
                           Workflow Engine
                                  │
                           Tool Registry
                                  │
                              Validator
                                  │
                             SU Executor
                                  │
                              sufilter
                                  │
                                  ▼
                            Project History
```

## Directory structure

```text
agentic-seismic-unix/
├── app.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
│
├── config/
│   └── agent.yaml
│
├── agent/
│   ├── __init__.py
│   ├── seismic_agent.py
│   ├── provider_factory.py
│   ├── openai_agent.py  # compatibility shim
│   ├── prompts.py
│   ├── toolkit.py
│   ├── providers/
│   │   ├── base.py
│   │   ├── openclaw_provider.py
│   │   └── openai_provider.py
│   └── README.md
│
├── su/
│   ├── registry.py
│   ├── validator.py
│   ├── executor.py
│   └── importer.py
│
├── tools/
│   ├── sufilter.yaml
│   ├── inspect_dataset.yaml
│   ├── inspect_frequency.yaml
│   └── compare_datasets.yaml
│
├── seismic/
│   ├── io.py
│   ├── spectrum.py
│   ├── qc.py
│   └── plotting.py
│
├── workflow/
│   ├── engine.py
│   └── history.py
│
├── project/
│   ├── project.py
│   └── state.py
│
├── knowledge/
│   └── filtering.md
│
├── recipes/
│   └── bandpass_qc.yaml
│
├── source/
└── data/
```


## Agent provider configuration

Provider selection is deployment configuration, not a UI control.

The default file is:

```text
config/agent.yaml
```

Default:

```yaml
provider: openclaw
fallback_provider: null

openclaw:
  base_url: http://127.0.0.1:18789/v1
  model: openclaw/default
  credential_env: OPENCLAW_GATEWAY_TOKEN
  agent_id: null

openai:
  model: gpt-5.6
  api_key_env: OPENAI_API_KEY
```

### Default: local OpenClaw

OpenClaw must expose its OpenResponses-compatible endpoint. In the OpenClaw Gateway configuration enable:

```json5
{
  gateway: {
    http: {
      endpoints: {
        responses: { enabled: true }
      }
    }
  }
}
```

Copy the environment template:

```bash
cp .env.example .env
```

Set the Gateway credential used by your OpenClaw auth mode:

```text
OPENCLAW_GATEWAY_TOKEN=your_gateway_token_or_password
```

The supplied Docker Compose uses `network_mode: host`, which is appropriate for the target Linux/OCI deployment and allows the container to reach an OpenClaw Gateway that remains bound to host loopback at `127.0.0.1:18789`.

If your OpenClaw deployment uses a dedicated agent, set either:

```yaml
openclaw:
  model: openclaw/my-seismic-agent
```

or set `agent_id` and keep `model: openclaw`.

### Optional: direct OpenAI API

Change:

```yaml
provider: openai
```

and set:

```text
OPENAI_API_KEY=your_api_key
```

The default direct model is:

```text
gpt-5.6
```

No automatic OpenClaw → OpenAI fallback is enabled. `fallback_provider` is deliberately `null` so a deployment does not silently change model/provider, credentials, cost surface, or audit behavior.

You may override the selected provider for a deployment with:

```text
AGENT_PROVIDER=openai
```

but the preferred persistent setting is `config/agent.yaml`.

## Provider architecture

```text
Streamlit
   ↓
SeismicAgent
   ↓
AgentProvider
  ├── OpenClawProvider  ← default
  └── OpenAIProvider    ← optional
   ↓
Same four client-side seismic tools
   ↓
Approval gate
   ↓
Workflow Engine → Validator → SU Executor
```

OpenClaw is used as the reasoning/model-routing runtime only. Seismic Unix tools are **not** exposed as OpenClaw shell/exec tools. They remain client-side functions owned by this application.

## Build and run

Put the official Seismic Unix source tarball under `source/` using the existing V0.2 convention, then:

```bash
docker compose build
docker compose up -d
```

Open:

```text
http://YOUR_VM_IP:8501
```

or route your existing Cloudflare Tunnel to `http://localhost:8501`.

## First agent test

After uploading a SEG-Y file, try:

```text
Inspect this dataset and tell me what you see.
```

Then:

```text
Inspect the frequency content and recommend a reasonable bandpass filter.
```

The agent should inspect the data and create a **Pending Approval** card. No filter is executed yet.

Click:

```text
Approve & Run sufilter
```

Then ask:

```text
Review the filter result. Did it improve the data?
```

The agent should call `compare_datasets` and discuss the machine-readable QC metrics.

## Human-in-the-loop behavior

### Auto

The agent may automatically execute:

- dataset inspection
- frequency inspection
- latest before/after QC comparison

### Approval required

The agent cannot automatically execute:

- `sufilter`

Its `apply_bandpass_filter` tool creates only a pending proposal. The Streamlit approval button is the authority that starts the existing deterministic processing workflow.

## Frequency inspection

`inspect_frequency` now reports a compact model-readable summary including:

- peak frequency
- 5/10/50/90/95% cumulative preview-spectrum power frequencies
- number of traces analyzed
- Nyquist frequency

These values are descriptive QC statistics. They are deliberately not labeled automatically as signal/noise boundaries; the agent must interpret them conservatively.

## Existing V0.2 fixes retained

This version is based on the user-edited V0.2 archive, including its improved SU endian detection and direct SU trace reading logic.

## Current limitations

- One active project/session in the Streamlit UI at a time.
- One agent, not a multi-agent architecture.
- One processing operation: `sufilter`.
- The QC metrics are intentionally simple.
- Chat history is kept in Streamlit session state, not yet persisted to project storage.
- The agent provider is selected per deployment: local OpenClaw by default, direct OpenAI API optionally.
- The app does not yet estimate processing cost or runtime.

## Recommended V0.4

After V0.3 is stable on real seismic data, the next useful step is the **QC reflection loop**:

```text
Agent proposes filter
   ↓
User approves
   ↓
sufilter
   ↓
QC metrics
   ↓
Agent reviews automatically
   ↓
Accept / propose adjusted filter
```

At that point the application starts to become genuinely iterative rather than only conversational.


## OpenClaw input-schema fix in V0.3.3

V0.3.1 replayed ChatGPT/OpenAI-style easy message objects to the OpenClaw
`/v1/responses` endpoint. Some OpenClaw versions reject that shape with:

```text
400 input: Invalid input
```

V0.3.3 uses the documented OpenResponses string input for each new OpenClaw
turn and supplies a stable per-project `user` key so the Gateway can preserve
session context. Tool continuations still use `function_call_output` with
`previous_response_id`. OpenAI direct mode continues to use explicit message
history.

A minimal Gateway smoke test is:

```bash
curl -sS http://127.0.0.1:18789/v1/responses \
  -H "Authorization: Bearer $OPENCLAW_GATEWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"openclaw/default","input":"hello"}'
```


## V0.3.3 OpenClaw tool-selection fix

OpenClaw supports caller-supplied client function tools, but `tool_choice: auto`
allows the underlying model to answer without calling one. For explicit seismic
data requests, V0.3.3 pins the first read-only tool deterministically:

- dataset/general inspection -> `inspect_dataset`
- spectrum/frequency/filter recommendation -> `inspect_frequency`
- review of a completed filter -> `compare_datasets`

After the first tool result, the agent returns to `tool_choice: auto`, allowing
it to explain the evidence or propose the approval-gated bandpass tool. The
runtime prompt also explicitly tells the model that a project dataset is loaded
and that the supplied client-side tools are available.

This avoids the failure mode where the model replies that it cannot access a
dataset even though the application has already loaded one.

## v0.3.4 OpenClaw compatibility change

OpenClaw's `/v1/responses` endpoint enforces pinned/required client tool calls: if the selected backend agent does not emit a matching structured `function_call`, the Gateway returns HTTP 502. Some OpenClaw backend/model combinations may therefore fail even though the Gateway accepted the tool schema.

V0.3.4 defaults OpenClaw to:

```yaml
openclaw:
  tool_strategy: application_routed
```

In this mode, obvious read-only seismic intents are routed by the application:

```text
inspect dataset       -> inspect_dataset
frequency / spectrum  -> inspect_frequency
review filter result  -> compare_datasets
```

The application executes the read-only inspection tool first and sends its structured result to OpenClaw as authoritative application evidence. OpenClaw then performs interpretation/reasoning. Client-side tools remain available with `tool_choice=auto`, but correctness no longer depends on a forced OpenClaw function call.

OpenAI direct mode continues to use native Responses API function calling.

If a future OpenClaw backend reliably emits client-side function calls, you can test:

```yaml
openclaw:
  tool_strategy: native
```

For production deployments, `application_routed` is the recommended default.
