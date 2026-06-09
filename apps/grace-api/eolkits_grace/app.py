from __future__ import annotations

import asyncio
import base64
import json
import secrets
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from fastapi import BackgroundTasks, FastAPI, Form, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response

from . import pricing
from .config import settings
from .email import render_audit_delivery_email, send_email
from .security import sha256_hex, verify_github_signature, verify_stripe_signature
from .store import Store
from .stripe_client import (
    create_checkout_session,
    create_refund,
    retrieve_checkout_session,
)


RUNNER_DIR = Path(__file__).resolve().parents[2] / "runner"
if RUNNER_DIR.exists() and str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

ALLOWED_EXTENSIONS = {".yaml", ".yml", ".json", ".tf", ".tfvars", ".js", ".ts", ".py", ".txt"}
OVERRIDE_LABEL = "override:ci-failure"
CI_FAILURE_CONCLUSIONS = {"failure", "timed_out"}
DRAIN_INTERVAL_SECONDS = 30

app = FastAPI(title="EOLkits GRACE API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.public_site_url, "https://eolkits.com"],
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"],
)

store = Store(settings.db_path)
_drain_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup() -> None:
    # Fail closed: refuse to run in production without live secrets.
    settings.require_runtime_secrets()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    # Drain any jobs that were durably queued but not completed before a restart.
    if settings.environment.strip().lower() != "test":
        global _drain_task
        _drain_task = asyncio.create_task(_drain_loop())


@app.on_event("shutdown")
async def shutdown() -> None:
    if _drain_task:
        _drain_task.cancel()


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "env": settings.environment,
        "storage": "filesystem",
        "database": "sqlite",
        "runner": "http" if settings.runner_url else "inline" if settings.enable_inline_runner else "disabled",
    }


@app.get("/status")
@app.get("/status.json")
async def status() -> dict[str, Any]:
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "overall": "healthy",
        "environment": settings.environment,
        "components": {
            "uploads": {"ok": settings.uploads_dir.exists(), "path": str(settings.uploads_dir)},
            "reports": {"ok": settings.reports_dir.exists(), "path": str(settings.reports_dir)},
            "stripe": {"ok": settings.stripe_is_live, "mode": "live" if settings.stripe_is_live else "test"},
            "email": {"ok": bool(settings.resend_api_key), "configured": bool(settings.resend_api_key)},
            "runner": {"ok": bool(settings.runner_url or settings.enable_inline_runner), "url": bool(settings.runner_url)},
        },
        "recent_jobs": store.recent_jobs(20),
        "funnel_7d": store.event_counts(7),
    }


# ---- uploads ----------------------------------------------------------------- #


@app.post("/upload/presign")
async def upload_presign(request: Request) -> dict[str, Any]:
    body = await request.json()
    filename = Path(str(body.get("filename") or "")).name
    size = int(body.get("size") or 0)
    if not filename:
        raise HTTPException(status_code=400, detail="filename required")
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail={"error": "invalid_file_type", "allowed": sorted(ALLOWED_EXTENSIONS)})
    if size and size > settings.max_upload_bytes:
        raise HTTPException(status_code=400, detail={"error": "file_too_large", "maxSize": settings.max_upload_bytes})

    upload_id = secrets.token_urlsafe(18).replace("-", "").replace("_", "")[:24]
    meta = {
        "filename": filename,
        "contentType": body.get("contentType") or "application/octet-stream",
        "size": size,
        "uploadedAt": datetime.now(UTC).isoformat(),
    }
    store.put_json(f"upload:{upload_id}", meta, ttl_seconds=3600 * 24 * 30)
    return {
        "uploadId": upload_id,
        "uploadUrl": f"{settings.public_api_url}/upload/{upload_id}",
        "expiresIn": 3600 * 24 * 30,
        "maxSize": settings.max_upload_bytes,
    }


@app.put("/upload/{upload_id}")
async def upload_file(upload_id: str, request: Request) -> dict[str, Any]:
    meta = store.get_json(f"upload:{upload_id}")
    if not meta:
        raise HTTPException(status_code=404, detail="upload not found or expired")
    body = await request.body()
    if len(body) > settings.max_upload_bytes:
        raise HTTPException(status_code=400, detail="file too large")
    path = _upload_path(upload_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    meta.update(
        {
            "received": True,
            "receivedAt": datetime.now(UTC).isoformat(),
            "sha256": sha256_hex(body),
            "bytes": len(body),
        }
    )
    store.put_json(f"upload:{upload_id}", meta, ttl_seconds=3600 * 24 * 30)
    return {"success": True, "uploadId": upload_id, "sha256": meta["sha256"]}


@app.get("/upload/{upload_id}")
async def get_upload(upload_id: str) -> FileResponse:
    meta = store.get_json(f"upload:{upload_id}")
    path = _upload_path(upload_id)
    if not meta or not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path, media_type=meta.get("contentType") or "application/octet-stream", filename=meta.get("filename") or "upload")


@app.get("/upload/report/{sha}")
async def get_report(sha: str) -> FileResponse:
    if not _valid_sha(sha):
        raise HTTPException(status_code=400, detail="invalid report hash")
    path = settings.reports_dir / f"{sha}.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="report not found")
    return FileResponse(path, media_type="application/pdf", filename=f"eolkits-audit-{sha[:8]}.pdf")


# ---- checkout ---------------------------------------------------------------- #


@app.post("/api/audit/checkout")
async def audit_checkout(
    request: Request,
    email: str = Form(...),
    deadline: str | None = Form(None),
    upload_id: str | None = Form(None),
    upload_url: str | None = Form(None),
    source: str | None = Form(None),
    utm_source: str | None = Form(None),
    utm_medium: str | None = Form(None),
    utm_campaign: str | None = Form(None),
    kit: str | None = Form(None),
) -> Response:
    # SSRF hardening: never trust an arbitrary upload_url. Accept an upload_id
    # (preferred) or extract one only from a URL that points at our own host,
    # then validate the upload actually exists locally.
    resolved_id = _resolve_upload_id(upload_id, upload_url)
    if not resolved_id:
        raise HTTPException(status_code=400, detail="upload_id required")
    meta = store.get_json(f"upload:{resolved_id}")
    if not meta:
        raise HTTPException(status_code=404, detail="upload not found or expired")

    tier = pricing.audit_price_for_deadline(deadline)
    price_id = tier["stripe_price_id"]
    price = int(tier["price_usd"])
    attribution = _attribution(source, utm_source, utm_medium, utm_campaign, kit)
    session = create_checkout_session(
        settings,
        sku="audit",
        email=email,
        price_id=price_id,
        price_usd=price,
        metadata={"upload_id": resolved_id, "deadline": deadline or "", **attribution},
        success_path="/success/?sku=audit&session_id={CHECKOUT_SESSION_ID}",
        cancel_path="/audit/?cancelled=1",
    )
    store.record_event("checkout_started", {"sku": "audit", "deadline": deadline, **attribution})
    return _checkout_response(request, session["url"], price, session["mode"])


@app.post("/api/pack/checkout")
async def pack_checkout(
    request: Request,
    email: str = Form(...),
    repo: str = Form(...),
    installation_id: str | None = Form(None),
    source: str | None = Form(None),
    utm_source: str | None = Form(None),
    utm_medium: str | None = Form(None),
    utm_campaign: str | None = Form(None),
    kit: str | None = Form(None),
) -> Response:
    # Require the GitHub App to be installed on the repo BEFORE charging, so we
    # never take money for a PR we cannot open.
    _require_repo_installed(repo, installation_id)
    price_id = pricing.price_id_for_sku("migration_pack")
    price = int(pricing.expected_amount_cents("migration_pack") or 149900) // 100
    attribution = _attribution(source, utm_source, utm_medium, utm_campaign, kit)
    session = create_checkout_session(
        settings,
        sku="migration_pack",
        email=email,
        price_id=price_id,
        price_usd=price,
        metadata={"repo": repo, "installation_id": installation_id or "", **attribution},
        success_path="/success/?sku=pack&session_id={CHECKOUT_SESSION_ID}",
        cancel_path="/pack/?cancelled=1",
    )
    store.record_event("checkout_started", {"sku": "migration_pack", **attribution})
    return _checkout_response(request, session["url"], price, session["mode"])


@app.post("/api/drift/checkout")
async def drift_checkout(
    request: Request,
    email: str = Form(...),
    repo: str | None = Form(None),
    iam_role: str | None = Form(None),
    source: str | None = Form(None),
    utm_source: str | None = Form(None),
    utm_medium: str | None = Form(None),
    utm_campaign: str | None = Form(None),
) -> Response:
    # Drift Watch is recurring ($19/mo) -> subscription-mode Checkout Session.
    price_id = pricing.price_id_for_sku("drift_watch")
    price = int(pricing.expected_amount_cents("drift_watch") or 1900) // 100
    attribution = _attribution(source, utm_source, utm_medium, utm_campaign, None)
    session = create_checkout_session(
        settings,
        sku="drift_watch",
        email=email,
        price_id=price_id,
        price_usd=price,
        metadata={"repo": repo or "", "iam_role": iam_role or "", **attribution},
        success_path="/success/?sku=drift&session_id={CHECKOUT_SESSION_ID}",
        cancel_path="/drift/?cancelled=1",
        mode="subscription",
    )
    store.record_event("checkout_started", {"sku": "drift_watch", **attribution})
    return _checkout_response(request, session["url"], price, session["mode"])


@app.post("/api/events")
async def record_event(request: Request) -> dict[str, Any]:
    """First-party funnel beacon. No third-party tracker; stores source/utm/kit/
    deadline/sku so conversion drop-offs are visible and attributable."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    name = str(body.get("event") or body.get("name") or "view")[:64]
    store.record_event(
        name,
        {
            "source": body.get("source"),
            "utm_source": body.get("utm_source"),
            "utm_medium": body.get("utm_medium"),
            "utm_campaign": body.get("utm_campaign"),
            "kit": body.get("kit"),
            "deadline": body.get("deadline"),
            "sku": body.get("sku"),
            "path": body.get("path"),
            "meta": body.get("meta"),
        },
    )
    return {"ok": True}


# ---- webhooks ---------------------------------------------------------------- #


@app.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    stripe_signature: str | None = Header(None),
) -> Response:
    payload = await request.body()
    if not verify_stripe_signature(payload, stripe_signature, settings.stripe_webhook_secret):
        raise HTTPException(status_code=400, detail="invalid signature")
    event = json.loads(payload)
    event_id = event.get("id")
    if not event_id:
        raise HTTPException(status_code=400, detail="missing event id")

    # Durable idempotency: record the event atomically. A duplicate delivery
    # short-circuits without re-fulfilling.
    if not store.record_stripe_event(event_id, event.get("type") or "unknown", event):
        return Response("Already processed", media_type="text/plain")

    try:
        if event.get("type") == "checkout.session.completed":
            session_obj = event.get("data", {}).get("object", {})
            session_id = session_obj.get("id")
            if session_id:
                _ingest_paid_session(session_id, background_tasks)
        store.mark_stripe_event(event_id, "processed")
    except HTTPException:
        store.mark_stripe_event(event_id, "rejected")
        raise
    except Exception as exc:  # pragma: no cover - defensive
        store.mark_stripe_event(event_id, "error")
        raise HTTPException(status_code=500, detail=f"processing error: {exc}") from exc
    return Response("OK", media_type="text/plain")


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str | None = Header(None),
    x_hub_signature_256: str | None = Header(None),
) -> Response:
    payload_bytes = await request.body()
    if not verify_github_signature(payload_bytes, x_hub_signature_256, settings.github_webhook_secret):
        raise HTTPException(status_code=400, detail="invalid signature")
    payload = json.loads(payload_bytes or b"{}")

    if x_github_event == "installation" and payload.get("action") in {"created", "new_permissions_accepted"}:
        _persist_installation(payload.get("installation", {}), payload.get("repositories") or [])
    if x_github_event == "installation_repositories":
        install = payload.get("installation", {})
        for repo in payload.get("repositories_added") or []:
            _map_repo_to_installation(repo.get("full_name"), install.get("id"), (install.get("account") or {}).get("login"))
        for repo in payload.get("repositories_removed") or []:
            store.delete(f"github:repo:{repo.get('full_name')}")
    if x_github_event == "push":
        repo = (payload.get("repository") or {}).get("full_name")
        for commit in payload.get("commits") or []:
            if ".no-eolkits" in (commit.get("added") or []) or ".no-eolkits" in (commit.get("modified") or []):
                store.put_json(f"no-eolkits:{repo}", {"blockedAt": datetime.now(UTC).isoformat()}, ttl_seconds=86400 * 365)
            if ".no-eolkits" in (commit.get("removed") or []):
                store.delete(f"no-eolkits:{repo}")

    # Refund guarantee: CI failure on a paid migration PR triggers an automatic,
    # idempotent refund unless the buyer waived it with the override label.
    if x_github_event in {"check_run", "check_suite"}:
        _handle_ci_event(x_github_event, payload, background_tasks)
    return Response("OK", media_type="text/plain")


# ---- GitHub App install flow ------------------------------------------------- #


@app.get("/pack/install")
async def pack_install() -> dict[str, Any]:
    # Prefer the real, public installation URL for the already-registered App.
    if settings.github_app_slug:
        return {
            "installUrl": f"https://github.com/apps/{settings.github_app_slug}/installations/new",
            "appSlug": settings.github_app_slug,
        }
    # Fallback (first-time bootstrap only): app-manifest create flow.
    manifest = {
        "name": "EOLkits Migration Bot",
        "url": settings.public_site_url,
        "callback_urls": [f"{settings.public_site_url}/pack/callback"],
        "setup_url": f"{settings.public_api_url}/pack/setup",
        "webhook_url": f"{settings.public_api_url}/webhook/github",
        "redirect_url": f"{settings.public_site_url}/pack/installed",
        "setup_on_install": True,
        "default_permissions": {
            "contents": "write",
            "pull_requests": "write",
            "metadata": "read",
            "checks": "read",
        },
        "default_events": ["push", "pull_request", "check_run", "check_suite", "installation", "installation_repositories"],
    }
    encoded = base64.b64encode(json.dumps(manifest).encode("utf-8")).decode("ascii")
    return {"installUrl": f"https://github.com/settings/apps/new?manifest={encoded}", "manifest": manifest}


@app.get("/pack/setup")
async def pack_setup(installation_id: str | None = None, setup_action: str | None = None) -> Response:
    """GitHub redirects here after an install. Persist the installation and its
    repos (fetched via the App), then bounce the user back to the site."""
    if installation_id:
        try:
            _fetch_and_persist_installation(installation_id)
        except Exception:
            # Non-fatal: the installation webhook will also persist the mapping.
            pass
    return RedirectResponse(f"{settings.public_site_url}/pack/?installed={installation_id or ''}", status_code=303)


# ---- license / verify / support (unchanged behavior) ------------------------- #


@app.post("/api/license/inquiry")
async def license_inquiry(background_tasks: BackgroundTasks, email: str = Form(...), company: str = Form(...), repos: int | None = Form(None)) -> dict[str, Any]:
    _enqueue_job(
        {
            "type": "license_inquiry",
            "email": email,
            "company": company,
            "repos": repos,
            "submittedAt": datetime.now(UTC).isoformat(),
        },
        background_tasks,
    )
    return {"received": True, "message": "License inquiry received. Check your email within 24 hours."}


@app.get("/api/license/verify")
async def verify_license(key: str) -> dict[str, Any]:
    data = store.get_json(f"license:{key}")
    if not data:
        raise HTTPException(status_code=404, detail={"valid": False, "error": "Invalid license key"})
    if datetime.fromisoformat(data["expiresAt"]) < datetime.now(UTC):
        raise HTTPException(status_code=403, detail={"valid": False, "error": "License expired", "expiredAt": data["expiresAt"]})
    return {
        "valid": True,
        "company": data["company"],
        "expiresAt": data["expiresAt"],
        "features": ["rule_feed", "private_rules", "unlimited_runs"],
    }


@app.post("/api/license/validate")
async def validate_license(request: Request) -> dict[str, Any]:
    body = await request.json()
    key = body.get("key")
    if not key:
        raise HTTPException(status_code=400, detail={"valid": False, "error": "Missing license key"})
    result = await verify_license(key)
    store.put_json(
        f"license:usage:{key}:{datetime.now(UTC).timestamp()}",
        {"action": body.get("action") or "validate", "timestamp": datetime.now(UTC).isoformat()},
        ttl_seconds=86400 * 365,
    )
    return {"valid": True, "action": body.get("action") or "validate", "timestamp": datetime.now(UTC).isoformat(), **result}


@app.get("/verify/{sha}")
async def verify_report(sha: str) -> dict[str, Any]:
    data = store.get_json(f"verify:{sha}")
    if not data:
        raise HTTPException(status_code=404, detail={"valid": False, "error": "Hash not found"})
    return {"valid": True, "sha256": sha, **data}


@app.get("/api/verify/{sha}")
async def verify_report_api(sha: str) -> dict[str, Any]:
    return await verify_report(sha)


@app.post("/support/ask")
async def support_ask(request: Request) -> dict[str, Any]:
    body = await request.json()
    question = str(body.get("question") or "").lower()
    if not question:
        raise HTTPException(status_code=400, detail="Missing question")
    canned = {
        "pricing": "See https://eolkits.com/#pricing for current pricing. CLI is free (MIT). Paid tiers: Audit PDF, Migration Pack, Org License, Drift Watch.",
        "refund": "Migration Pack purchases auto-refund if CI fails within 7 days. Audit PDFs are non-refundable but include verification. Terms: https://eolkits.com/legal/terms",
        "install": "Install any kit from https://github.com/ntoledo319/EOLkits. Each kit README has package-specific setup.",
        "license": "CLI code is MIT licensed. Paid tiers grant access to hosted automation and reports.",
        "support": "Use GitHub Discussions at https://github.com/ntoledo319/EOLkits/discussions.",
    }
    for keyword, answer in canned.items():
        if keyword in question:
            return {"answer": answer, "source": "canned", "confidence": "high"}
    return {
        "answer": "See the EOLkits docs at https://eolkits.com/ or ask on GitHub Discussions: https://github.com/ntoledo319/EOLkits/discussions",
        "source": "canned_fallback",
    }


# ---- partners ---------------------------------------------------------------- #


@app.post("/partners/signup")
async def partner_signup(
    email: str = Form(...),
    display_name: str = Form(...),
    domain: str = Form(...),
) -> dict[str, Any]:
    slug = _slugify(display_name)
    if not slug:
        raise HTTPException(status_code=400, detail="invalid display_name")
    if store.get_json(f"partner:{slug}"):
        raise HTTPException(status_code=409, detail={"error": "partner_slug_taken", "slug": slug})
    account_id, onboarding_url = _create_partner_account(email)
    partner_secret = secrets.token_urlsafe(24)
    record = {
        "slug": slug,
        "email": email,
        "display_name": display_name,
        "domain": domain,
        "domain_verified": False,
        "stripe_account_id": account_id,
        "secret_sha256": sha256_hex(partner_secret.encode("utf-8")),
        "logo_url": None,
        "created_at": datetime.now(UTC).isoformat(),
    }
    store.put_json(f"partner:{slug}", record)
    return {
        "slug": slug,
        "onboarding_url": onboarding_url,
        "partner_secret": partner_secret,  # shown once; used as X-Partner-Secret
        "verification_record": {
            "type": "TXT",
            "host": f"_eolkits.{domain}",
            "value": f"eolkits-verification={slug}",
        },
    }


@app.post("/partners/verify/{slug}")
async def partner_verify(slug: str) -> dict[str, Any]:
    record = store.get_json(f"partner:{slug}")
    if not record:
        raise HTTPException(status_code=404, detail="partner not found")
    expected = f"eolkits-verification={slug}"
    verified = False
    try:
        response = requests.get(
            "https://cloudflare-dns.com/dns-query",
            params={"name": f"_eolkits.{record['domain']}", "type": "TXT"},
            headers={"Accept": "application/dns-json"},
            timeout=10,
        )
        response.raise_for_status()
        answers = response.json().get("Answer") or []
        verified = any(expected in answer.get("data", "") for answer in answers)
    except requests.RequestException:
        verified = False
    record["domain_verified"] = verified
    store.put_json(f"partner:{slug}", record)
    return {"slug": slug, "verified": verified}


@app.post("/partners/{slug}/audit")
async def partner_audit(
    slug: str,
    background_tasks: BackgroundTasks,
    buyer_email: str = Form(...),
    upload_id: str | None = Form(None),
    upload_url: str | None = Form(None),
    stripe_session_id: str = Form(...),
    x_partner_secret: str | None = Header(None),
) -> dict[str, Any]:
    record = store.get_json(f"partner:{slug}")
    if not record:
        raise HTTPException(status_code=404, detail="partner not found")
    # AuthN: partner must present the secret issued at signup.
    if not _partner_secret_ok(record, x_partner_secret):
        raise HTTPException(status_code=401, detail="invalid partner secret")
    # The audit must correspond to a real, paid Stripe session.
    paid = _verify_partner_session(stripe_session_id)
    resolved_id = _resolve_upload_id(upload_id, upload_url)
    if not resolved_id or not store.get_json(f"upload:{resolved_id}"):
        raise HTTPException(status_code=404, detail="upload not found")

    branded = bool(record.get("domain_verified"))
    _enqueue_job(
        {
            "type": "audit_pdf",
            "sku": "audit",
            "email": buyer_email,
            "buyer_email": buyer_email,
            "upload_id": resolved_id,
            "stripe_session_id": stripe_session_id,
            "branding": {
                "partner_slug": slug,
                "display_name": record["display_name"],
                "logo_url": record.get("logo_url"),
            }
            if branded
            else None,
            "transfer": {
                "partner_account": record.get("stripe_account_id"),
                "partner_share": 0.7,
                "payment_intent": paid.get("payment_intent"),
                "amount": paid.get("amount_total"),
            },
        },
        background_tasks,
        dedupe_key=f"partner-audit:{stripe_session_id}",
    )
    return {"ok": True, "queued": True}


# ---- helpers ----------------------------------------------------------------- #


def _upload_path(upload_id: str) -> Path:
    if "/" in upload_id or "\\" in upload_id or not upload_id:
        raise HTTPException(status_code=400, detail="invalid upload id")
    return settings.uploads_dir / upload_id / "file"


def _resolve_upload_id(upload_id: str | None, upload_url: str | None) -> str | None:
    """Return a safe, local upload id. An upload_url is only honored when it
    points at our own host; arbitrary URLs are rejected (SSRF)."""
    if upload_id:
        candidate = Path(upload_id).name
        return candidate or None
    if not upload_url:
        return None
    parsed = urlparse(upload_url)
    own_hosts = {urlparse(settings.public_api_url).netloc, urlparse(settings.public_site_url).netloc}
    if parsed.netloc and parsed.netloc not in own_hosts:
        raise HTTPException(status_code=400, detail="upload_url must reference an eolkits upload")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[-2] == "upload":
        return parts[-1]
    return None


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:32]


def _attribution(
    source: str | None,
    utm_source: str | None,
    utm_medium: str | None,
    utm_campaign: str | None,
    kit: str | None,
) -> dict[str, str]:
    """Build the non-empty attribution metadata that rides along on the Stripe
    session so source/utm/kit survive into the purchase row and analytics."""
    fields = {
        "source": source,
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "kit": kit,
    }
    return {key: str(value)[:200] for key, value in fields.items() if value}


def _partner_secret_ok(record: dict[str, Any], provided: str | None) -> bool:
    if settings.is_demo_stripe and not record.get("secret_sha256"):
        return True
    if not provided:
        return False
    import hmac as _hmac

    return _hmac.compare_digest(record.get("secret_sha256", ""), sha256_hex(provided.encode("utf-8")))


def _verify_partner_session(session_id: str) -> dict[str, Any]:
    if settings.is_demo_stripe:
        return {"payment_intent": None, "amount_total": None}
    session = retrieve_checkout_session(settings, session_id)
    return _validate_paid_session(session, expected_sku="audit")


def _create_partner_account(email: str) -> tuple[str, str]:
    if settings.is_demo_stripe:
        account = "acct_dummy_" + secrets.token_hex(8)
        return account, f"{settings.public_site_url}/partners/onboarding-demo"
    response = requests.post(
        "https://api.stripe.com/v1/accounts",
        headers={
            "Authorization": f"Bearer {settings.stripe_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"type": "express", "email": email, "capabilities[transfers][requested]": "true"},
        timeout=30,
    )
    response.raise_for_status()
    account = response.json()["id"]
    link = requests.post(
        "https://api.stripe.com/v1/account_links",
        headers={
            "Authorization": f"Bearer {settings.stripe_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "account": account,
            "refresh_url": f"{settings.public_site_url}/partners/onboarding",
            "return_url": f"{settings.public_site_url}/partners/onboarded",
            "type": "account_onboarding",
        },
        timeout=30,
    )
    link.raise_for_status()
    return account, link.json()["url"]


def _valid_sha(sha: str) -> bool:
    return len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)


def _checkout_response(request: Request, url: str, price: int, mode: str) -> Response:
    accept = request.headers.get("accept", "")
    if "text/html" in accept and "application/json" not in accept:
        return RedirectResponse(url, status_code=303)
    return JSONResponse({"url": url, "price": price, "mode": mode})


# ---- payment validation + fulfillment ---------------------------------------- #


def _validate_paid_session(session: dict[str, Any], expected_sku: str | None = None) -> dict[str, Any]:
    """Verify an authoritative Stripe session before fulfilling. Raises 400 on
    any mismatch so we never fulfill (or refund-link) an unpaid/forged order."""
    if session.get("status") not in (None, "complete"):
        raise HTTPException(status_code=400, detail="session not complete")
    if session.get("payment_status") not in ("paid", "no_payment_required"):
        raise HTTPException(status_code=400, detail="session not paid")
    metadata = session.get("metadata") or {}
    if metadata.get("project") != "eolkits":
        raise HTTPException(status_code=400, detail="session not an eolkits order")
    sku = metadata.get("sku")
    if expected_sku and sku != expected_sku:
        raise HTTPException(status_code=400, detail="unexpected sku")
    if session.get("currency") not in ("usd", None):
        raise HTTPException(status_code=400, detail="unexpected currency")
    # In production the charge must be livemode.
    livemode = session.get("livemode")
    if settings.is_production and livemode is False:
        raise HTTPException(status_code=400, detail="test-mode session rejected in production")

    price_id = _session_price_id(session) or metadata.get("price_id")
    allowed = pricing.allowed_price_ids(sku) if sku else set()
    if price_id and allowed and price_id not in allowed:
        raise HTTPException(status_code=400, detail="price id not recognized for sku")
    amount_total = session.get("amount_total")
    expected_amount = pricing.expected_amount_cents(sku, price_id) if sku else None
    if expected_amount is not None and amount_total is not None and amount_total != expected_amount:
        raise HTTPException(status_code=400, detail="amount mismatch")

    return {
        "sku": sku,
        "price_id": price_id,
        "amount_total": amount_total,
        "currency": session.get("currency"),
        "livemode": bool(livemode),
        "payment_intent": _payment_intent_id(session),
        "email": session.get("customer_email") or metadata.get("email"),
        "metadata": metadata,
    }


def _session_price_id(session: dict[str, Any]) -> str | None:
    line_items = (session.get("line_items") or {}).get("data") or []
    if line_items:
        return ((line_items[0] or {}).get("price") or {}).get("id")
    return None


def _payment_intent_id(session: dict[str, Any]) -> str | None:
    pi = session.get("payment_intent")
    if isinstance(pi, dict):
        return pi.get("id")
    return pi


def _ingest_paid_session(session_id: str, background_tasks: BackgroundTasks) -> None:
    """Retrieve the authoritative session, validate it, durably record the
    purchase, and durably queue fulfillment."""
    if settings.is_demo_stripe:
        return  # No live Stripe in sandbox; fulfillment is exercised via tests.
    session = retrieve_checkout_session(settings, session_id)
    info = _validate_paid_session(session)
    metadata = info["metadata"]
    sku = info["sku"]
    store.record_purchase(
        session_id=session_id,
        payment_intent=info["payment_intent"],
        sku=sku,
        email=info["email"],
        price_id=info["price_id"],
        amount=info["amount_total"],
        currency=info["currency"],
        livemode=info["livemode"],
        repo=metadata.get("repo"),
        deadline=metadata.get("deadline"),
        metadata=metadata,
    )
    _queue_fulfillment(session_id, sku, info["email"], metadata, background_tasks)


def _queue_fulfillment(
    session_id: str,
    sku: str | None,
    email: str | None,
    metadata: dict[str, Any],
    background_tasks: BackgroundTasks,
) -> None:
    if sku == "audit":
        _enqueue_job(
            {"type": "audit_pdf", "sessionId": session_id, "email": email, "upload_id": metadata.get("upload_id"), "deadline": metadata.get("deadline")},
            background_tasks,
            dedupe_key=f"fulfill:{session_id}",
        )
    elif sku == "migration_pack":
        _enqueue_job(
            {"type": "migration_pr", "sessionId": session_id, "email": email, "repo": metadata.get("repo"), "installationId": metadata.get("installation_id")},
            background_tasks,
            dedupe_key=f"fulfill:{session_id}",
        )
    elif sku == "org_license":
        _enqueue_job(
            {"type": "license_key", "sessionId": session_id, "email": email, "company": metadata.get("company")},
            background_tasks,
            dedupe_key=f"fulfill:{session_id}",
        )
    elif sku == "drift_watch":
        _enqueue_job(
            {"type": "drift_watch_setup", "sessionId": session_id, "email": email, "repo": metadata.get("repo"), "iam_role": metadata.get("iam_role")},
            background_tasks,
            dedupe_key=f"fulfill:{session_id}",
        )


# ---- job queue / drainer ----------------------------------------------------- #


def _enqueue_job(job: dict[str, Any], background_tasks: BackgroundTasks, dedupe_key: str | None = None) -> int:
    job_id = store.enqueue(str(job.get("type") or "unknown"), job, dedupe_key=dedupe_key)
    background_tasks.add_task(_run_job, job_id, job)
    return job_id


def _run_job(job_id: int, job: dict[str, Any]) -> None:
    # Only one of {inline background task, startup drainer} processes a job.
    if not store.try_claim(job_id):
        return
    try:
        _execute_job(job_id, job)
        store.mark_job(job_id, "completed")
    except Exception as exc:
        status = store.schedule_retry_or_deadletter(job_id, str(exc))
        if status == "dead_letter":
            store.mark_job(job_id, "dead_letter", str(exc))


def _execute_job(job_id: int, job: dict[str, Any]) -> None:
    result = _dispatch_runner(job)
    if job.get("type") == "audit_pdf":
        _fulfill_audit(result, job)
        if job.get("transfer"):
            _settle_partner_transfer(job, result)
    if job.get("type") == "license_key":
        _store_license(job)
    if job.get("type") == "migration_pr":
        _record_pr_linkage(job, result)


async def _drain_loop() -> None:
    while True:
        try:
            await asyncio.get_event_loop().run_in_executor(None, _drain_once)
        except Exception:  # pragma: no cover - never let the loop die
            pass
        await asyncio.sleep(DRAIN_INTERVAL_SECONDS)


def _drain_once() -> None:
    for job_row in store.claim_pending_jobs():
        _run_job(int(job_row["id"]), job_row["payload"])


def _dispatch_runner(job: dict[str, Any]) -> dict[str, Any]:
    job = _attach_runner_upload_ref(job)
    if settings.runner_url:
        response = requests.post(
            settings.runner_url,
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {settings.runner_token}"} if settings.runner_token else {}),
            },
            json=job,
            timeout=900,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("success") is False:
            raise RuntimeError(json.dumps(data))
        return data.get("result") or {}
    if settings.enable_inline_runner:
        from main import run_job

        return run_job(job)
    store.enqueue(str(job.get("type") or "unknown"), job, status="requires_runner")
    return {"queued": True}


def _attach_runner_upload_ref(job: dict[str, Any]) -> dict[str, Any]:
    """Convert an upload_id into a runner-consumable reference WITHOUT trusting
    a client-supplied URL. Inline runner gets a local path; an HTTP runner gets
    a server-derived URL on our own host."""
    upload_id = job.get("upload_id")
    if not upload_id:
        return job
    job = dict(job)
    if not settings.runner_url:
        job["upload_path"] = str(_upload_path(upload_id))
    else:
        job["upload_url"] = f"{settings.public_api_url}/upload/{upload_id}"
    return job


def _fulfill_audit(result: dict[str, Any], job: dict[str, Any]) -> None:
    email = result.get("email") or job.get("email")
    input_hash = result.get("input_hash")
    pdf_base64 = result.get("pdf_base64")
    rule_pack_version = result.get("rule_pack_version")
    generated_at = result.get("generated_at")
    if not all([email, input_hash, pdf_base64, rule_pack_version, generated_at]):
        raise RuntimeError("audit result missing delivery fields")

    pdf_bytes = base64.b64decode(pdf_base64)
    report_path = settings.reports_dir / f"{input_hash}.pdf"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(pdf_bytes)
    store.put_json(
        f"verify:{input_hash}",
        {"generatedAt": generated_at, "rulePackVersion": rule_pack_version},
        ttl_seconds=86400 * 30,
    )
    pdf_url = f"{settings.public_api_url}/upload/report/{input_hash}"
    verify_url = f"{settings.public_site_url}/verify/?hash={input_hash}"
    send_email(
        settings,
        to=email,
        subject="Your EOLkits Audit is ready",
        html=render_audit_delivery_email(
            pdf_url=pdf_url,
            verify_url=verify_url,
            rule_pack_version=rule_pack_version,
            input_sha=input_hash,
        ),
    )


def _settle_partner_transfer(job: dict[str, Any], result: dict[str, Any]) -> None:
    transfer = job.get("transfer") or {}
    account = transfer.get("partner_account")
    amount = transfer.get("amount")
    payment_intent = transfer.get("payment_intent")
    if settings.is_demo_stripe or not account or not amount or not payment_intent:
        return
    share = float(transfer.get("partner_share", 0.7))
    transfer_amount = int(round(int(amount) * share))
    from .stripe_client import stripe_request

    stripe_request(
        settings,
        "/v1/transfers",
        {
            "amount": str(transfer_amount),
            "currency": "usd",
            "destination": account,
            "transfer_group": payment_intent,
            "metadata[project]": "eolkits",
            "metadata[partner_slug]": (job.get("branding") or {}).get("partner_slug", ""),
        },
        idempotency_key=f"transfer:{payment_intent}",
    )


def _record_pr_linkage(job: dict[str, Any], result: dict[str, Any]) -> None:
    session_id = job.get("sessionId")
    pr_url = result.get("pr_url")
    pr_number = result.get("pr_number")
    repo = result.get("repo") or job.get("repo")
    if session_id and pr_url and pr_number and repo:
        store.link_purchase_pr(session_id, pr_url=pr_url, pr_number=int(pr_number), repo=repo)


def _store_license(job: dict[str, Any]) -> None:
    company = job.get("company") or "EOLkits customer"
    email = job.get("email")
    key = "-".join(secrets.token_hex(4).upper() for _ in range(4))
    expires = datetime.now(UTC).replace(microsecond=0)
    expires = expires.replace(year=expires.year + 1)
    store.put_json(
        f"license:{key}",
        {
            "company": company,
            "email": email,
            "createdAt": datetime.now(UTC).isoformat(),
            "expiresAt": expires.isoformat(),
            "key": key,
        },
        ttl_seconds=86400 * 366,
    )


# ---- GitHub installation mapping + refund engine ----------------------------- #


def _persist_installation(install: dict[str, Any], repositories: list[dict[str, Any]]) -> None:
    install_id = install.get("id")
    account = (install.get("account") or {}).get("login")
    store.put_json(
        f"github:install:{install_id}",
        {
            "id": install_id,
            "account": account,
            "repositories": [r.get("full_name") for r in repositories],
            "createdAt": datetime.now(UTC).isoformat(),
        },
    )
    for repo in repositories:
        _map_repo_to_installation(repo.get("full_name"), install_id, account)


def _map_repo_to_installation(full_name: str | None, install_id: Any, account: str | None) -> None:
    if not full_name:
        return
    store.put_json(f"github:repo:{full_name}", {"installation_id": install_id, "account": account})


def _repo_installation(repo: str) -> Any | None:
    mapping = store.get_json(f"github:repo:{repo}")
    return mapping.get("installation_id") if mapping else None


def _require_repo_installed(repo: str, installation_id: str | None) -> None:
    if settings.is_demo_stripe:
        return
    mapped = _repo_installation(repo)
    if mapped is None:
        raise HTTPException(status_code=409, detail={"error": "app_not_installed", "repo": repo, "installUrl": f"https://github.com/apps/{settings.github_app_slug}/installations/new" if settings.github_app_slug else None})
    if installation_id and str(mapped) != str(installation_id):
        raise HTTPException(status_code=409, detail={"error": "installation_mismatch", "repo": repo})


def _fetch_and_persist_installation(installation_id: str) -> None:
    """Use the App to read the installation + its repos and persist the mapping."""
    from migration_pr import _generate_jwt, _gh_headers  # type: ignore

    app_jwt = _generate_jwt()
    inst = requests.get(
        f"https://api.github.com/app/installations/{installation_id}",
        headers={"Authorization": f"Bearer {app_jwt}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
        timeout=15,
    )
    inst.raise_for_status()
    install = inst.json()
    token_resp = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers={"Authorization": f"Bearer {app_jwt}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
        timeout=15,
    )
    token_resp.raise_for_status()
    token = token_resp.json()["token"]
    repos_resp = requests.get(
        "https://api.github.com/installation/repositories",
        headers=_gh_headers(token),
        timeout=15,
    )
    repos_resp.raise_for_status()
    repos = repos_resp.json().get("repositories", [])
    _persist_installation(install, repos)


def _handle_ci_event(event_name: str, payload: dict[str, Any], background_tasks: BackgroundTasks) -> None:
    obj = payload.get(event_name, {})
    if obj.get("status") != "completed":
        return
    if obj.get("conclusion") not in CI_FAILURE_CONCLUSIONS:
        return
    repo = (payload.get("repository") or {}).get("full_name")
    if not repo:
        return
    for pr in obj.get("pull_requests") or []:
        pr_number = pr.get("number")
        if pr_number is not None:
            background_tasks.add_task(_maybe_refund_for_pr, repo, int(pr_number))


def _maybe_refund_for_pr(repo: str, pr_number: int) -> None:
    purchase = store.get_purchase_by_pr(repo, pr_number)
    if not purchase or purchase.get("refunded"):
        return
    if purchase.get("sku") != "migration_pack":
        return
    # Within the advertised refund window?
    window_days = int(pricing.load_pricing().get("skus", {}).get("migration_pack", {}).get("refund_window_days", 7))
    created = purchase.get("created_at")
    try:
        created_dt = datetime.fromisoformat(created) if created else None
    except ValueError:
        created_dt = None
    if created_dt and datetime.now(UTC) - created_dt > timedelta(days=window_days):
        return
    # Respect the buyer's waiver.
    try:
        if _pr_has_override_label(repo, pr_number):
            return
    except Exception:
        # Can't confirm the override state -> don't silently refund; flag review.
        store.enqueue("refund_review", {"repo": repo, "pr_number": pr_number, "session_id": purchase.get("session_id")}, dedupe_key=f"refund-review:{purchase.get('session_id')}")
        return
    payment_intent = purchase.get("payment_intent")
    session_id = purchase.get("session_id")
    if not payment_intent or not session_id:
        return
    if settings.is_demo_stripe:
        store.mark_refunded(session_id, "re_demo")
        return
    refund = create_refund(
        settings,
        payment_intent=payment_intent,
        reason="requested_by_customer",
        idempotency_key=f"refund:{session_id}",
    )
    if store.mark_refunded(session_id, refund.get("id", "")):
        email = purchase.get("email")
        if email:
            send_email(
                settings,
                to=email,
                subject="EOLkits Migration Pack — automatic refund issued",
                html=f"<p>CI failed on your migration PR (#{pr_number} in {repo}) within the {window_days}-day guarantee window, so your purchase has been refunded.</p>",
            )


def _pr_has_override_label(repo: str, pr_number: int) -> bool:
    install_id = _repo_installation(repo)
    if install_id is None:
        raise RuntimeError("no installation for repo")
    from migration_pr import _gh_headers, mint_installation_token  # type: ignore

    token = mint_installation_token(str(install_id))
    resp = requests.get(
        f"https://api.github.com/repos/{repo}/issues/{pr_number}/labels",
        headers=_gh_headers(token),
        timeout=15,
    )
    resp.raise_for_status()
    labels = {item.get("name") for item in resp.json()}
    return OVERRIDE_LABEL in labels
