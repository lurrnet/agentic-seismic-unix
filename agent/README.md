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


## V0.4 reflection path

`SeismicAgent.review_latest_filter()` receives deterministic QC from `AgentToolkit.compare_datasets()` plus a residual frequency summary for the current filtered dataset. It asks the selected provider for a small JSON decision (`accept` or `adjust`). `adjust` is converted into the existing approval-gated `sufilter` proposal only after application-side validation.
