# Execution Layer

Deterministic Python scripts. The orchestrator (Claude) calls these instead of doing the work itself.

## Conventions

- **One script = one job.** Keep scripts focused. Easier to test, easier to reuse.
- **Read secrets from `.env`** via `python-dotenv`. Never hardcode keys.
- **Write intermediates to `.tmp/`.** Never to the repo root.
- **Print structured output** (JSON when feasible) so the orchestrator can parse results.
- **Exit non-zero on failure** with a useful stderr message.
- **Comment the WHY**, not the WHAT. Names should explain the what.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Adding a new script

1. Check if an existing script already does this (or can be extended).
2. Add to `requirements.txt` if you introduce a new dependency.
3. Add a one-line header comment describing inputs, outputs, side effects.
4. Reference it from the relevant directive in `directives/`.
