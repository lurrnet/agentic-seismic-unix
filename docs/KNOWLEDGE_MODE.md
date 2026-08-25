# Knowledge Mode

Version 0.9.4 keeps the Agent chat available before a SEG-Y dataset is loaded.

## Modes

### Knowledge Mode

Active when no project dataset is loaded.

The agent can:

- explain Seismic Unix commands and parameters;
- answer questions using the local SU documentation knowledge layer;
- discuss general seismic-processing concepts and workflows.

The application does **not** construct an `AgentToolkit`, expose application tool schemas, create processing proposals, or execute seismic commands in this mode.

Dataset-specific questions must be answered as general guidance only. The agent should state that a SEG-Y dataset must be loaded before it can inspect sampling, spectra, amplitudes, headers, geometry, gathers, velocities, or make validated dataset-specific processing recommendations.

### Project Mode

Active after SEG-Y import succeeds.

The existing application-routed inspection, proposal, validation, approval, processing, QC, provenance, and security controls are available.

## Trust boundary

Knowledge Mode is not a UI-only restriction. Its request path is separate from Project Mode:

```text
No dataset
  -> Knowledge Mode
  -> provider + local SU knowledge
  -> text response only

Dataset loaded
  -> Project Mode
  -> application inspection / validators / proposal bridge / SU execution
```

Knowledge Mode returns no pending action and no application tool trace. Local SU documentation remains reference knowledge only and never grants execution authority.
