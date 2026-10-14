# Security

## Reporting a vulnerability

Report suspected vulnerabilities privately by email to support@thesingulant.ai.

Do not open public issues, pull requests or discussions that contain exploit details, credentials, API keys or infrastructure details. Please give us reasonable time to investigate and fix an issue before any public disclosure.

## Scope

In scope: the Singulant Proof source code in this repository and its public API implementation (`POST /v1/proof/verify`, `GET /healthz`, and the bundled web UI).

Out of scope: Nansen services and data, third-party hosting outages, social engineering, and systems not shipped in this repository.

## What this policy does not claim

Singulant Proof has not undergone a formal third-party security audit or certification. There is no bug bounty program. Reports are handled through responsible, coordinated disclosure.

## Secrets

Never commit `NANSEN_API_KEY` or any other credential. Use a local `.env` file, which is ignored by git.
