"""Authenticated bridge and public synthetic-only simulator."""

import hashlib
import hmac
import os
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.schemas import AnalyzeResponse
from app.services import alert_policy, media, media_text, text_analysis
from app.services.extractors import ExtractionError
from app.services.media_config import MAX_BYTES

router = APIRouter(tags=["whatsapp"])
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


def authenticate(x_api_key: Annotated[str | None, Header()] = None) -> None:
    key = os.getenv("WHATSAPP_API_KEY", "")
    if (
        len(key) < 32
        or not x_api_key
        or not hmac.compare_digest(key.encode(), x_api_key.encode())
    ):
        raise HTTPException(401, "Bridge authentication required.")


class ConsentRequest(BaseModel):
    guardian: Digest
    enabled: bool


class ConsentStatus(BaseModel):
    enabled: bool


class Event(BaseModel):
    guardian: Digest
    sender: Digest
    text: Annotated[str, Field(min_length=1, max_length=12000)]


class Decision(BaseModel):
    reason: str
    should_alert: bool = False
    dry_run: bool = True
    risk_level: str | None = None
    rule_ids: list[str] = Field(default_factory=list)
    alert_user_text: str | None = None
    alert_guardian_text: str | None = None


def decide(
    result: AnalyzeResponse,
    guardian: str | None = None,
    sender: str = "",
    digest: str = "",
) -> Decision:
    reason = "below_threshold"
    if result.risk_level == "high":
        reason = (
            alert_policy.reserve(guardian, sender, digest) if guardian else "eligible"
        )
    eligible = reason == "eligible"
    ids = [
        rule for rule in result.rule_flags if rule in {f"R{i:02}" for i in range(1, 12)}
    ]
    reasons = ", ".join(ids) or "model risk"
    return Decision(
        reason=reason,
        should_alert=eligible,
        dry_run=guardian is None or alert_policy.dry_run(),
        risk_level=result.risk_level,
        rule_ids=ids,
        alert_user_text=f"Nigehbaan: High risk ({reasons}). Verify the request before sharing credentials or sending money."
        if eligible
        else None,
        alert_guardian_text=f"Nigehbaan: Your protected demo account received a high-risk message ({reasons})."
        if eligible
        else None,
    )


def permitted(guardian: str) -> bool:
    return alert_policy.opted_in() and alert_policy.consent(guardian)


def fingerprint(content: bytes) -> str:
    return hmac.new(
        os.environ["WHATSAPP_API_KEY"].encode(), content, hashlib.sha256
    ).hexdigest()


@router.get("/consent", dependencies=[Depends(authenticate)])
def get_consent(guardian: Digest) -> ConsentStatus:
    return ConsentStatus(enabled=permitted(guardian))


@router.post("/consent", dependencies=[Depends(authenticate)])
def set_consent(body: ConsentRequest) -> ConsentStatus:
    return ConsentStatus(
        enabled=alert_policy.consent(
            body.guardian, body.enabled and alert_policy.opted_in()
        )
    )


@router.post("/whatsapp/event", dependencies=[Depends(authenticate)])
def event(body: Event) -> Decision:
    if not permitted(body.guardian):
        return Decision(reason="consent_required")
    return decide(
        text_analysis.analyze(body.text),
        body.guardian,
        body.sender,
        fingerprint(body.text.encode()),
    )


def analyze_media(data: bytes, content_type: str | None) -> AnalyzeResponse:
    try:
        _, extracted = media.extract(data, content_type)
    except ExtractionError as error:
        raise HTTPException(error.status, "Media could not be analyzed.") from None
    ml_input, _ = media_text.model_text(extracted.text)
    return text_analysis.analyze(extracted.text, ml_text=ml_input)


@router.post("/whatsapp/media", dependencies=[Depends(authenticate)])
async def media_event(
    guardian: Annotated[Digest, Form()],
    sender: Annotated[Digest, Form()],
    file: Annotated[UploadFile, File()],
) -> Decision:
    try:
        if not await run_in_threadpool(permitted, guardian):
            return Decision(reason="consent_required")
        data = await file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "Media exceeds upload limit.")
        result = await run_in_threadpool(analyze_media, data, file.content_type)
        return await run_in_threadpool(
            decide, result, guardian, sender, fingerprint(data)
        )
    finally:
        await file.close()


@router.post("/simulate/whatsapp")
def simulate(case: Literal["scam", "normal"] = "scam") -> Decision:
    text = (
        "Foran OTP bhejo https://example.com"
        if case == "scam"
        else "Kal class kitne bajay hai?"
    )
    return decide(text_analysis.analyze(text))
