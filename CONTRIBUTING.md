# Contributing

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Tests

```bash
pytest
```

The default suite runs offline. The live Nansen test skips unless `NANSEN_API_KEY` is set. CI runs the offline suite on every pull request.

## Pull requests

- Keep each pull request focused on one change and include tests for behavior changes.
- The adjudicator must stay deterministic: the same evidence set must produce the same scores and verdict.
- Do not let a language model choose or override the verdict.

## Claim boundaries

Singulant Proof reports what the submitted evidence supports. Do not add copy or features that present it as authorizing transactions, establishing identity or reputation, guaranteeing truth, or giving investment advice.

## Secrets

Never commit API keys, `.env` files, raw provider dumps or credentials. Report security issues privately as described in [SECURITY.md](SECURITY.md).
