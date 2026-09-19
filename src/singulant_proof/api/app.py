"""FastAPI app: POST /v1/proof/verify, GET /healthz, static web UI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from singulant_proof import ATTRIBUTION, CTA, __version__
from singulant_proof.integrations.nansen.client import NansenClient
from singulant_proof.integrations.nansen.errors import NansenAuthError, NansenError
from singulant_proof.integrations.nansen.normalize import build_evidence_set
from singulant_proof.integrations.nansen.schemas import SMART_MONEY_CHAINS, TGM_CHAINS, TGM_TIMEFRAMES
from singulant_proof.proof.adjudicator import PIPELINE_STAGES, ProofResult, run_proof
from singulant_proof.proof.claim import CLAIM_ID, ClaimError, parse_claim
from singulant_proof.proof.evidence import EvidenceSet, Observation, TokenContext, new_evidence_set

WEB_DIR = Path(__file__).resolve().parents[3] / "web"

ClaimLiteral = Literal["SMART_MONEY_IS_ACCUMULATING_THIS_TOKEN"]


class VerifyRequest(BaseModel):
    chain: str = Field(..., min_length=1, max_length=32)
    token_address: str = Field(..., min_length=1, max_length=128)
    claim: ClaimLiteral = "SMART_MONEY_IS_ACCUMULATING_THIS_TOKEN"
    timeframe: Literal["5m", "1h", "6h", "12h", "1d", "7d"] = "1d"
    demo: bool = False


class HealthResponse(BaseModel):
    status: str
    version: str
    attribution: str
    cta: str
    nansen_key_configured: bool


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip() in {"1", "true", "TRUE", "yes", "YES"}


def _normalize_chain(chain: str) -> str:
    return chain.strip().lower()


def _normalize_token(token_address: str) -> str:
    value = token_address.strip()
    if value.startswith("0x") or value.startswith("0X"):
        return "0x" + value[2:].lower()
    return value


def synthetic_evidence(chain: str, token_address: str, timeframe: str) -> EvidenceSet:
    """Labeled synthetic docket for local UI / tests. Not a Nansen dump."""
    context = TokenContext(
        token_address=token_address,
        token_symbol="DEMO",
        chain=chain,
        trader_count=14,
        token_age_days=420,
        market_cap_usd=85_000_000.0,
        token_sectors=["demo"],
    )
    observations = (
        Observation("nf:1h", "smart_money_netflow", "net_flow_1h_usd", 12_500.0, "usd", "1h", "smart_money", "primary"),
        Observation("nf:24h", "smart_money_netflow", "net_flow_24h_usd", 48_000.0, "usd", "24h", "smart_money", "primary"),
        Observation("nf:7d", "smart_money_netflow", "net_flow_7d_usd", 210_000.0, "usd", "7d", "smart_money", "primary"),
        Observation("nf:30d", "smart_money_netflow", "net_flow_30d_usd", 95_000.0, "usd", "30d", "smart_money", "primary"),
        Observation("nf:trader_count", "smart_money_netflow", "trader_count", 14.0, "count", "30d", "smart_money", "context"),
        Observation("nf:token_age_days", "smart_money_netflow", "token_age_days", 420.0, "days", None, None, "context"),
        Observation("nf:market_cap_usd", "smart_money_netflow", "market_cap_usd", 85_000_000.0, "usd", None, None, "context"),
        Observation("tgm:smart_trader:net", "tgm_flow_intelligence", "smart_trader_net_flow_usd", 62_000.0, "usd", timeframe, "smart_trader", "cohort"),
        Observation("tgm:smart_trader:avg", "tgm_flow_intelligence", "smart_trader_avg_flow_usd", 4_400.0, "usd", timeframe, "smart_trader", "context"),
        Observation("tgm:smart_trader:wallets", "tgm_flow_intelligence", "smart_trader_wallet_count", 11.0, "count", timeframe, "smart_trader", "context"),
        Observation("tgm:top_pnl:net", "tgm_flow_intelligence", "top_pnl_net_flow_usd", -38_000.0, "usd", timeframe, "top_pnl", "cohort"),
        Observation("tgm:top_pnl:avg", "tgm_flow_intelligence", "top_pnl_avg_flow_usd", 9_100.0, "usd", timeframe, "top_pnl", "context"),
        Observation("tgm:top_pnl:wallets", "tgm_flow_intelligence", "top_pnl_wallet_count", 6.0, "count", timeframe, "top_pnl", "context"),
        Observation("tgm:whale:net", "tgm_flow_intelligence", "whale_net_flow_usd", 15_000.0, "usd", timeframe, "whale", "cohort"),
        Observation("tgm:whale:avg", "tgm_flow_intelligence", "whale_avg_flow_usd", None, "usd", timeframe, "whale", "context"),
        Observation("tgm:whale:wallets", "tgm_flow_intelligence", "whale_wallet_count", 3.0, "count", timeframe, "whale", "context"),
        Observation("tgm:exchange:net", "tgm_flow_intelligence", "exchange_net_flow_usd", 25_000.0, "usd", timeframe, "exchange", "cohort"),
        Observation("tgm:exchange:avg", "tgm_flow_intelligence", "exchange_avg_flow_usd", None, "usd", timeframe, "exchange", "context"),
        Observation("tgm:exchange:wallets", "tgm_flow_intelligence", "exchange_wallet_count", 0.0, "count", timeframe, "exchange", "context"),
        Observation("tgm:fresh_wallets:net", "tgm_flow_intelligence", "fresh_wallets_net_flow_usd", None, "usd", timeframe, "fresh_wallets", "cohort"),
        Observation("tgm:fresh_wallets:avg", "tgm_flow_intelligence", "fresh_wallets_avg_flow_usd", None, "usd", timeframe, "fresh_wallets", "context"),
        Observation("tgm:fresh_wallets:wallets", "tgm_flow_intelligence", "fresh_wallets_wallet_count", 0.0, "count", timeframe, "fresh_wallets", "context"),
        Observation("tgm:public_figure:net", "tgm_flow_intelligence", "public_figure_net_flow_usd", None, "usd", timeframe, "public_figure", "cohort"),
        Observation("tgm:public_figure:avg", "tgm_flow_intelligence", "public_figure_avg_flow_usd", None, "usd", timeframe, "public_figure", "context"),
        Observation("tgm:public_figure:wallets", "tgm_flow_intelligence", "public_figure_wallet_count", None, "count", timeframe, "public_figure", "context"),
    )
    return new_evidence_set(
        claim=parse_claim(CLAIM_ID),
        chain=chain,
        token_address=token_address,
        context=context,
        observations=observations,
        provenance=(),
        warnings=["TGM_EXCHANGE_WALLET_COUNT_ALWAYS_ZERO"],
        tgm_timeframe=timeframe,
    )


def collect_from_nansen(
    *,
    chain: str,
    token_address: str,
    timeframe: str,
    api_key: str | None = None,
) -> tuple[EvidenceSet, list[str]]:
    extra: list[str] = []
    netflow = None
    tgm = None
    key = (api_key if api_key is not None else os.environ.get("NANSEN_API_KEY", "")).strip()
    if not key:
        raise NansenAuthError("NANSEN_API_KEY is not set", status_code=401)

    with NansenClient(key) as client:
        if chain in SMART_MONEY_CHAINS and chain != "all":
            try:
                netflow = client.smart_money_netflow(chains=[chain], token_address=token_address)
            except NansenError as exc:
                extra.append(f"NETFLOW_ERROR:{exc.status_code or 'unknown'}")
        else:
            extra.append("NETFLOW_UNSUPPORTED_CHAIN")

        if chain in TGM_CHAINS:
            try:
                tgm = client.tgm_flow_intelligence(chain=chain, token_address=token_address, timeframe=timeframe)
            except NansenError as exc:
                extra.append(f"TGM_ERROR:{exc.status_code or 'unknown'}")
        else:
            extra.append("TGM_UNSUPPORTED_CHAIN")

    evidence = build_evidence_set(
        chain=chain,
        token_address=token_address,
        timeframe=timeframe,
        netflow=netflow,
        tgm=tgm,
        extra_warnings=extra,
    )
    return evidence, extra


def verify_claim(
    *,
    chain: str,
    token_address: str,
    claim: str,
    timeframe: str,
    demo: bool,
) -> ProofResult:
    parse_claim(claim)
    if timeframe not in TGM_TIMEFRAMES:
        raise ClaimError(f"unsupported timeframe {timeframe}")

    stages = list(PIPELINE_STAGES)
    if demo:
        if not _env_flag("SINGULANT_PROOF_ALLOW_DEMO"):
            raise HTTPException(status_code=400, detail="demo mode is disabled (set SINGULANT_PROOF_ALLOW_DEMO=1)")
        evidence = synthetic_evidence(chain, token_address, timeframe)
        return run_proof(evidence, stages_completed=tuple(stages), synthetic=True)

    try:
        evidence, _ = collect_from_nansen(chain=chain, token_address=token_address, timeframe=timeframe)
    except NansenAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return run_proof(evidence, stages_completed=tuple(stages))


def create_app() -> FastAPI:
    app = FastAPI(
        title="Singulant Proof",
        description="Don't ask AI to confirm your thesis. Make it try to break it.",
        version=__version__,
    )
    # CORS is owned by nginx in production. Do not add CORSMiddleware:
    # allow_origins=["*"] stacked with nginx and browsers rejected duplicate ACAO.

    @app.get("/healthz", response_model=HealthResponse)
    def healthz() -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=__version__,
            attribution=ATTRIBUTION,
            cta=CTA,
            nansen_key_configured=bool(os.environ.get("NANSEN_API_KEY", "").strip()),
        )

    @app.post("/v1/proof/verify")
    def verify(request: VerifyRequest) -> dict[str, Any]:
        chain = _normalize_chain(request.chain)
        token = _normalize_token(request.token_address)
        try:
            result = verify_claim(
                chain=chain,
                token_address=token,
                claim=request.claim,
                timeframe=request.timeframe,
                demo=request.demo,
            )
        except ClaimError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return result.as_public_dict()

    if WEB_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(WEB_DIR / "index.html")

        @app.get("/app.js")
        def app_js() -> FileResponse:
            return FileResponse(WEB_DIR / "app.js", media_type="text/javascript")

        @app.get("/styles.css")
        def styles() -> FileResponse:
            return FileResponse(WEB_DIR / "styles.css", media_type="text/css")

    return app


app = create_app()
