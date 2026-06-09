from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _load_app(tmp_path, monkeypatch, **env_overrides):
    root = Path(__file__).resolve().parents[3]
    api_root = root / "apps" / "grace-api"
    runner_root = root / "apps" / "runner"
    for path in (api_root, runner_root):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))

    env = {
        "ENVIRONMENT": "test",
        "EOLKITS_DATA_DIR": str(tmp_path),
        "STRIPE_KEY": "sk_test_dummy",
        "STRIPE_WEBHOOK_SECRET": "whsec_test",
        "PUBLIC_SITE_URL": "https://eolkits.com",
        "PUBLIC_API_URL": "https://eolkits.com",
        "EOLKITS_INLINE_RUNNER": "0",
    }
    env.update(env_overrides)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    for name in list(sys.modules):
        if name == "eolkits_grace" or name.startswith("eolkits_grace."):
            del sys.modules[name]
    mod = importlib.import_module("eolkits_grace.app")
    return mod, TestClient(mod.app)


def test_health_reports_grace_native_primitives(tmp_path, monkeypatch):
    _, client = _load_app(tmp_path, monkeypatch)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["storage"] == "filesystem"
    assert data["database"] == "sqlite"


def test_upload_checkout_verify_flow_uses_local_state(tmp_path, monkeypatch):
    mod, client = _load_app(tmp_path, monkeypatch)

    presign = client.post(
        "/upload/presign",
        json={"filename": "template.yaml", "contentType": "text/yaml", "size": 18},
    )
    assert presign.status_code == 200
    upload_url = presign.json()["uploadUrl"]
    upload_id = presign.json()["uploadId"]

    uploaded = client.put(f"/upload/{upload_id}", content=b"Runtime: nodejs20.x")
    assert uploaded.status_code == 200
    assert uploaded.json()["success"] is True

    checkout = client.post(
        "/api/audit/checkout",
        data={"email": "buyer@example.com", "upload_url": upload_url},
        headers={"accept": "application/json"},
    )
    assert checkout.status_code == 200
    assert checkout.json()["url"].startswith("https://checkout.stripe.com/test")

    sha = "a" * 64
    mod.store.put_json("verify:" + sha, {"generatedAt": "now", "rulePackVersion": "test"})
    verify = client.get(f"/verify/{sha}")
    assert verify.status_code == 200
    assert verify.json()["valid"] is True


def test_github_pack_install_points_to_grace_api(tmp_path, monkeypatch):
    _, client = _load_app(tmp_path, monkeypatch)
    response = client.get("/pack/install")
    assert response.status_code == 200
    manifest = response.json()["manifest"]
    assert manifest["webhook_url"] == "https://eolkits.com/webhook/github"


def test_stripe_webhook_rejects_bad_signature(tmp_path, monkeypatch):
    _, client = _load_app(tmp_path, monkeypatch)
    response = client.post(
        "/webhook/stripe",
        content=json.dumps({"id": "evt_1", "type": "checkout.session.completed"}),
        headers={"stripe-signature": "bad"},
    )
    assert response.status_code == 400


def test_partner_signup_and_audit_queue(tmp_path, monkeypatch):
    mod, client = _load_app(tmp_path, monkeypatch)

    signup = client.post(
        "/partners/signup",
        data={
            "email": "partner@example.com",
            "display_name": "Acme Partners",
            "domain": "example.com",
        },
    )
    assert signup.status_code == 200
    assert signup.json()["slug"] == "acme-partners"
    partner_secret = signup.json()["partner_secret"]
    assert partner_secret
    assert mod.store.get_json("partner:acme-partners")["email"] == "partner@example.com"

    # An upload must exist locally before a partner audit can be queued.
    presign = client.post(
        "/upload/presign",
        json={"filename": "template.yaml", "contentType": "text/yaml", "size": 18},
    )
    upload_id = presign.json()["uploadId"]
    client.put(f"/upload/{upload_id}", content=b"Runtime: nodejs20.x")

    # Without the partner secret the request is rejected.
    unauth = client.post(
        "/partners/acme-partners/audit",
        data={
            "buyer_email": "buyer@example.com",
            "upload_id": upload_id,
            "stripe_session_id": "cs_123",
        },
    )
    assert unauth.status_code == 401

    audit = client.post(
        "/partners/acme-partners/audit",
        data={
            "buyer_email": "buyer@example.com",
            "upload_id": upload_id,
            "stripe_session_id": "cs_123",
        },
        headers={"x-partner-secret": partner_secret},
    )
    assert audit.status_code == 200
    assert audit.json() == {"ok": True, "queued": True}
    jobs = mod.store.recent_jobs()
    assert jobs[0]["type"] == "audit_pdf"
    assert jobs[0]["payload"]["email"] == "buyer@example.com"


def test_production_startup_fails_closed_without_secrets(tmp_path, monkeypatch):
    """ENVIRONMENT=production with sandbox/dummy secrets must refuse to start."""
    import importlib
    import sys as _sys

    root = Path(__file__).resolve().parents[3]
    for path in (root / "apps" / "grace-api", root / "apps" / "runner"):
        if str(path) not in _sys.path:
            _sys.path.insert(0, str(path))
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("EOLKITS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("STRIPE_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    for name in list(_sys.modules):
        if name == "eolkits_grace" or name.startswith("eolkits_grace."):
            del _sys.modules[name]
    cfg = importlib.import_module("eolkits_grace.config")
    settings = cfg.Settings()
    assert settings.is_production
    missing = settings.missing_production_secrets()
    assert any("STRIPE_KEY" in m for m in missing)
    with pytest.raises(RuntimeError):
        settings.require_runtime_secrets()


def test_stripe_webhook_is_idempotent_and_validates(tmp_path, monkeypatch):
    """A valid, signed checkout.session.completed fulfills exactly once; a
    duplicate delivery is a no-op; an unpaid session is rejected."""
    # A live-style key takes the non-demo validation/ingest path; we stub the
    # authoritative session retrieval + signature check below.
    mod, client = _load_app(tmp_path, monkeypatch, STRIPE_KEY="sk_live_dummytest")

    paid_session = {
        "id": "cs_live_1",
        "status": "complete",
        "payment_status": "paid",
        "currency": "usd",
        "amount_total": 29900,
        "livemode": False,
        "customer_email": "buyer@example.com",
        "payment_intent": "pi_1",
        "metadata": {"project": "eolkits", "sku": "audit", "upload_id": "abc", "price_id": "price_1TRoGjDL3cQl851oiIWR5JIa"},
        "line_items": {"data": [{"price": {"id": "price_1TRoGjDL3cQl851oiIWR5JIa"}}]},
    }
    monkeypatch.setattr(mod, "retrieve_checkout_session", lambda settings, sid: paid_session)
    monkeypatch.setattr(mod, "verify_stripe_signature", lambda *a, **k: True)
    # Don't actually run the runner during the webhook background task.
    monkeypatch.setattr(mod, "_run_job", lambda *a, **k: None)

    event = json.dumps({"id": "evt_paid_1", "type": "checkout.session.completed", "data": {"object": {"id": "cs_live_1"}}})
    r1 = client.post("/webhook/stripe", content=event, headers={"stripe-signature": "ok"})
    assert r1.status_code == 200
    assert r1.text == "OK"
    purchase = mod.store.get_purchase_by_session("cs_live_1")
    assert purchase and purchase["sku"] == "audit" and purchase["amount"] == 29900

    # Duplicate delivery -> already processed, no second purchase row mutation.
    r2 = client.post("/webhook/stripe", content=event, headers={"stripe-signature": "ok"})
    assert r2.status_code == 200
    assert r2.text == "Already processed"

    # An unpaid session is rejected.
    unpaid = dict(paid_session, id="cs_live_2", payment_status="unpaid")
    monkeypatch.setattr(mod, "retrieve_checkout_session", lambda settings, sid: unpaid)
    bad_event = json.dumps({"id": "evt_unpaid", "type": "checkout.session.completed", "data": {"object": {"id": "cs_live_2"}}})
    r3 = client.post("/webhook/stripe", content=bad_event, headers={"stripe-signature": "ok"})
    assert r3.status_code == 400


def test_events_beacon_records_funnel(tmp_path, monkeypatch):
    mod, client = _load_app(tmp_path, monkeypatch)
    r = client.post(
        "/api/events",
        json={"event": "view", "sku": "audit", "utm_source": "migrate", "kit": "al2023-gate"},
    )
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert mod.store.event_counts(7).get("view") == 1
    status = client.get("/status").json()
    assert status["funnel_7d"].get("view") == 1


def test_drift_checkout_uses_subscription_mode(tmp_path, monkeypatch):
    mod, client = _load_app(tmp_path, monkeypatch)
    r = client.post(
        "/api/drift/checkout",
        data={"email": "buyer@example.com", "repo": "owner/repo", "utm_source": "home"},
        headers={"accept": "application/json"},
    )
    assert r.status_code == 200
    # Demo Stripe returns the sandbox URL; the checkout_started event is recorded.
    assert r.json()["url"].startswith("https://checkout.stripe.com/test")
    assert mod.store.event_counts(7).get("checkout_started") == 1


def test_audit_checkout_propagates_attribution_metadata(tmp_path, monkeypatch):
    """source/utm/kit must ride along on the Stripe metadata (demo URL echoes it)."""
    mod, client = _load_app(tmp_path, monkeypatch)
    presign = client.post(
        "/upload/presign",
        json={"filename": "template.yaml", "contentType": "text/yaml", "size": 10},
    )
    upload_id = presign.json()["uploadId"]
    client.put(f"/upload/{upload_id}", content=b"Runtime: nodejs20.x")
    r = client.post(
        "/api/audit/checkout",
        data={
            "email": "buyer@example.com",
            "upload_id": upload_id,
            "deadline": "2026-06-30",
            "utm_source": "migrate",
            "kit": "lambda-lifeline",
        },
        headers={"accept": "application/json"},
    )
    assert r.status_code == 200
    url = r.json()["url"]
    assert "utm_source=migrate" in url and "kit=lambda-lifeline" in url


def test_surge_tier_matches_pricing(tmp_path, monkeypatch):
    mod, _ = _load_app(tmp_path, monkeypatch)
    from eolkits_grace import pricing

    assert pricing.audit_tier(3)["price_usd"] == 599
    assert pricing.audit_tier(20)["price_usd"] == 399
    assert pricing.audit_tier(365)["price_usd"] == 299
    # Boundaries are inclusive and match the canonical Price IDs verified live.
    assert pricing.audit_tier(7)["stripe_price_id"] == "price_1TRoEZDL3cQl851o9DFh1DIz"
    assert pricing.audit_tier(30)["stripe_price_id"] == "price_1TRoGiDL3cQl851ouqnljzMx"

