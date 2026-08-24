# Agent layer — V0.3.1

The agent layer now has a provider abstraction:

```text
SeismicAgent
  ↓
AgentProvider
  ├── OpenClawProvider
  └── OpenAIProvider
```

`config/agent.yaml` selects the provider. OpenClaw is the default.

Both providers expose the same Responses-style function-calling loop, so the seismic tool contract is unchanged:

- `inspect_dataset` — automatic/read-only
- `inspect_frequency` — automatic/read-only
- `compare_datasets` — automatic/read-only
- `apply_bandpass_filter` — proposal only; requires UI approval

The provider never receives arbitrary shell access. Approved processing still flows through the application's `WorkflowEngine -> Validator -> SUExecutor` path.
