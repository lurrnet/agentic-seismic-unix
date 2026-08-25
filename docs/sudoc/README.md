# Local SU Knowledge Layer

V0.9.2 adds a bounded, application-side Seismic Unix documentation retrieval layer.

The OpenClaw agent does **not** receive filesystem or web access. Instead, the web application:

1. inspects the current user request;
2. deterministically maps relevant concepts to SU commands;
3. reads up to a small number of local Markdown references from this directory;
4. injects those references as `APPLICATION_SU_KNOWLEDGE` for the current model request only.

The documents are command-reference material. They do not authorize execution and do not override:

- the application tool registry;
- YAML parameter schemas;
- deterministic validators;
- approval policy;
- project-state checks;
- observed seismic evidence.

Current coverage includes `sufilter`, `sugain`/AGC, `suwind`, `sushw`, `susort`, `suresamp`, `sumute`, `sustack`, `supef`, and `sunmo`.

The first release deliberately uses deterministic command/concept retrieval instead of a vector database. Embedding-based retrieval can be added later when the corpus expands to broader SU selfdoc/tutorial material.
