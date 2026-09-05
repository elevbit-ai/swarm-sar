# Contributing to SwarmSAR

Thanks for your interest in improving SwarmSAR.

## Development setup

```bash
git clone https://github.com/elevbit-ai/swarm-sar.git
cd swarm-sar
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Before you open a pull request

```bash
ruff check .
pytest
```

- Keep the core dependency-free; heavy dependencies belong behind an optional extra.
- New behaviour needs tests. The simulation is deterministic under a seed —
  please keep it that way.
- Follow the existing style; `ruff` enforces formatting and import order.

## Scope and acceptable use

SwarmSAR is a **search-and-rescue** framework. Contributions must stay within
that mission (see `RESPONSIBLE_USE.md`). Pull requests that add targeting,
weapons integration, or any capability intended to harm the people the system
detects will be declined.
