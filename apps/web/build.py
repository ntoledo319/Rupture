#!/usr/bin/env python3
"""
EOLkits Static Site Generator
Builds docs/ from templates and rule-pack data.
"""

import sys
import json
import re
import yaml
from pathlib import Path
from datetime import UTC, datetime, timedelta

# Jinja2 is the only external dependency
try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    print("Installing jinja2...")
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "jinja2"])
    from jinja2 import Environment, FileSystemLoader, select_autoescape


BASE_DIR = Path(__file__).parent
TEMPLATE_DIR = BASE_DIR / "templates"
DOCS_DIR = BASE_DIR.parent.parent / "docs"
PRICING_FILE = BASE_DIR.parent.parent / "pricing.yml"
PROJECT_BASE_PATH = "/EOLkits"
SITE_URL = "https://ntoledo319.github.io/EOLkits"
ROOT_RELATIVE_ATTR_RE = re.compile(
    r'(?P<prefix>\b(?:href|src|action)=["\'])(?P<path>/(?!/|EOLkits(?:/|["\'])))'
)
ROOT_RELATIVE_FETCH_RE = re.compile(
    r"(?P<prefix>fetch\([\"'])(?P<path>/(?!/|EOLkits(?:/|[\"'])))"
)


def load_pricing():
    """Load pricing configuration."""
    with open(PRICING_FILE) as f:
        return yaml.safe_load(f)


def normalize_project_links(html):
    """Make root-relative links work on the /EOLkits GitHub Pages project path."""

    def replace(match):
        return f"{match.group('prefix')}{PROJECT_BASE_PATH}{match.group('path')}"

    html = ROOT_RELATIVE_ATTR_RE.sub(replace, html)
    return ROOT_RELATIVE_FETCH_RE.sub(replace, html)


def get_days_until_deadline(deadline_str):
    """Calculate days until a deadline."""
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").replace(tzinfo=UTC)
        return (deadline - datetime.now(UTC)).days
    except Exception:
        return 999


def get_surge_price(base_price, days_until):
    """Calculate surge pricing based on deadline proximity."""
    if days_until <= 7:
        return base_price * 2  # $299 -> $599
    elif days_until <= 30:
        return int(base_price * 1.33)  # $299 -> ~$399
    return base_price


def build_audit_page(pricing):
    """Build the audit checkout page."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Audit PDF — EOLkits</title>
<style>
body{font-family:system-ui,-apple-system,sans-serif;max-width:800px;margin:0 auto;padding:2rem;line-height:1.6}
.brand{color:#2563eb;font-weight:600}
h1{margin-top:0}
.pricing{border:2px solid #e5e7eb;border-radius:8px;padding:1.5rem;margin:1.5rem 0}
.price{font-size:2rem;font-weight:700;color:#059669}
.tiers{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin:1rem 0}
.tier{border:1px solid #d1d5db;border-radius:6px;padding:1rem;text-align:center}
.tier.urgent{border-color:#dc2626;background:#fef2f2}
.tier.soon{border-color:#f59e0b;background:#fffbeb}
button{background:#2563eb;color:white;border:none;padding:0.75rem 1.5rem;border-radius:6px;font-size:1rem;cursor:pointer}
button:hover{background:#1d4ed8}
footer{margin-top:3rem;padding-top:1rem;border-top:1px solid #e5e7eb;color:#6b7280;font-size:0.875rem}
</style>
</head>
<body>
<a href="/" class="brand">← EOLkits</a>
<h1>Audit PDF</h1>
<p>Upload your IaC files, get a hash-anchored deterministic report scoring every finding by severity × blast-radius.</p>

<div class="pricing">
  <h2>Pricing</h2>
  <div class="tiers">
    <div class="tier">
      <strong>Standard</strong>
      <div class="price">$299</div>
      <p>More than 30 days until deadline</p>
    </div>
    <div class="tier soon">
      <strong>Surge (30d)</strong>
      <div class="price">$399</div>
      <p>Within 30 days of deadline</p>
    </div>
    <div class="tier urgent">
      <strong>Urgent (7d)</strong>
      <div class="price">$599</div>
      <p>Within 7 days of deadline</p>
    </div>
  </div>
  <p><small>All tiers include: hash-anchored PDF, verification URL, severity scoring, roll-forward roadmap, cost estimate</small></p>
</div>

<h2>How it works</h2>
<ol>
  <li>Upload your SAM/CDK/Terraform/Serverless files</li>
  <li>We scan for deprecated runtimes and breaking changes</li>
  <li>Receive PDF via email within 5 minutes</li>
  <li>Verify authenticity at <code>/verify/&lt;sha&gt;</code></li>
</ol>

<form action="https://eolkits-worker.eolkits-kits.workers.dev/api/audit/checkout" method="POST">
  <h3>Start Audit</h3>
  <p><input type="email" name="email" placeholder="your@email.com" required style="padding:0.5rem;width:300px"></p>
  <p><input type="file" name="files" multiple accept=".yaml,.yml,.json,.tf,.js,.ts,.py"></p>
  <button type="submit">Proceed to Checkout</button>
</form>

<footer>
  <p>Delivery within 5 minutes. Reports include SHA-256 hash of inputs for verification.</p>
  <p><a href="/legal/terms">Terms</a> · <a href="/legal/privacy">Privacy</a></p>
</footer>
</body>
</html>"""
    return html


def build_pack_page(pricing):
    """Build the Migration Pack checkout page."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Migration Pack — EOLkits</title>
<style>
body{font-family:system-ui,-apple-system,sans-serif;max-width:800px;margin:0 auto;padding:2rem;line-height:1.6}
.brand{color:#2563eb;font-weight:600}
h1{margin-top:0}
.price{font-size:3rem;font-weight:700;color:#059669}
.guarantee{background:#ecfdf5;border:2px solid #059669;border-radius:8px;padding:1.5rem;margin:1.5rem 0}
.guarantee h3{margin-top:0;color:#059669}
button{background:#2563eb;color:white;border:none;padding:0.75rem 1.5rem;border-radius:6px;font-size:1rem;cursor:pointer}
button:hover{background:#1d4ed8}
.steps{background:#f9fafb;border-radius:8px;padding:1.5rem;margin:1.5rem 0}
.steps ol{margin:0;padding-left:1.5rem}
footer{margin-top:3rem;padding-top:1rem;border-top:1px solid #e5e7eb;color:#6b7280;font-size:0.875rem}
</style>
</head>
<body>
<a href="/" class="brand">← EOLkits</a>
<h1>Migration Pack</h1>
<p class="price">$1,499</p>
<p>A real PR opened on your repository with codemods, IaC patches, canary plan, and rollback script.</p>

<div class="guarantee">
  <h3>Refund Guarantee</h3>
  <p>If your CI fails on the migration PR within 7 days, you are automatically refunded. No questions, no human in the loop.</p>
</div>

<div class="steps">
  <h3>What you get</h3>
  <ol>
    <li><strong>GitHub App Install</strong> — Grant read/write access to your repo</li>
    <li><strong>Automated Analysis</strong> — We scan for deprecated patterns</li>
    <li><strong>PR Created</strong> — Real PR with codemods and IaC patches within 5 minutes</li>
    <li><strong>CI Check</strong> — Run your existing tests</li>
    <li><strong>Auto-Refund</strong> — If CI fails and no override label added</li>
  </ol>
</div>

<h3>Install GitHub App</h3>
<p>First, install the EOLkits Migration Bot on your repository:</p>
<p><a href="https://eolkits-worker.eolkits-kits.workers.dev/pack/install" style="display:inline-block;background:#24292f;color:white;padding:0.75rem 1.5rem;border-radius:6px;text-decoration:none;font-weight:600">Install GitHub App</a></p>

<h3>Or Purchase Now</h3>
<form action="https://eolkits-worker.eolkits-kits.workers.dev/api/pack/checkout" method="POST">
  <p><input type="email" name="email" placeholder="your@email.com" required style="padding:0.5rem;width:300px"></p>
  <p><input type="text" name="repo" placeholder="owner/repo" required style="padding:0.5rem;width:300px"></p>
  <button type="submit">Purchase Migration Pack — $1,499</button>
</form>

<footer>
  <p>Refund auto-fires if CI fails within 7 days. <a href="/legal/terms">Terms</a> apply.</p>
  <p><a href="/">Home</a> · <a href="/legal/terms">Terms</a> · <a href="/legal/privacy">Privacy</a></p>
</footer>
</body>
</html>"""
    return html


def build_license_page(pricing):
    """Build the Org License page."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Org License — EOLkits</title>
<style>
body{font-family:system-ui,-apple-system,sans-serif;max-width:800px;margin:0 auto;padding:2rem;line-height:1.6}
.brand{color:#2563eb;font-weight:600}
h1{margin-top:0}
.price{font-size:3rem;font-weight:700;color:#7c3aed}
button{background:#2563eb;color:white;border:none;padding:0.75rem 1.5rem;border-radius:6px;font-size:1rem;cursor:pointer}
button:hover{background:#1d4ed8}
.features{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1rem;margin:1.5rem 0}
.feature{background:#f9fafb;border-radius:8px;padding:1rem}
footer{margin-top:3rem;padding-top:1rem;border-top:1px solid #e5e7eb;color:#6b7280;font-size:0.875rem}
</style>
</head>
<body>
<a href="/" class="brand">← EOLkits</a>
<h1>Organization License</h1>
<p class="price">$14,999<span style="font-size:1rem;font-weight:normal;color:#6b7280">/year</span></p>
<p>Unlimited runs, live rule-pack feed, and private rule extensions for your entire organization.</p>

<div class="features">
  <div class="feature">
    <h3>Live Rule Feed</h3>
    <p>Get new deprecation rules the moment they're published — no 7-day delay.</p>
  </div>
  <div class="feature">
    <h3>Private Rules</h3>
    <p>Define custom rules specific to your organization's infrastructure patterns.</p>
  </div>
  <div class="feature">
    <h3>Unlimited Runs</h3>
    <p>No caps on scans, audits, or PRs across all your repositories.</p>
  </div>
  <div class="feature">
    <h3>License Key</h3>
    <p>One key activates all features across your CI/CD pipelines.</p>
  </div>
</div>

<h3>Request License</h3>
<p>Organization licenses are provisioned manually after verification:</p>
<form action="https://eolkits-worker.eolkits-kits.workers.dev/api/license/inquiry" method="POST">
  <p><input type="email" name="email" placeholder="your@company.com" required style="padding:0.5rem;width:300px"></p>
  <p><input type="text" name="company" placeholder="Company name" required style="padding:0.5rem;width:300px"></p>
  <p><input type="number" name="repos" placeholder="Estimated repositories" style="padding:0.5rem;width:300px"></p>
  <button type="submit">Request License</button>
</form>

<footer>
  <p>License valid for one year from purchase. Auto-renewal optional.</p>
  <p><a href="/">Home</a> · <a href="/legal/terms">Terms</a> · <a href="/legal/privacy">Privacy</a></p>
</footer>
</body>
</html>"""
    return html


def load_deprecations():
    """Load deprecation data from rules."""
    deprecations_file = BASE_DIR.parent.parent / "rules" / "public" / "deprecations.yml"
    if deprecations_file.exists():
        with open(deprecations_file) as f:
            return yaml.safe_load(f)
    return {"deprecations": []}


def slugify(name):
    """Convert name to URL slug."""
    return (
        name.lower()
        .replace(" ", "-")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "-")
    )


def build_pricing_view(full_pricing):
    """Extract the canonical Audit/Migration-Pack facts (price + Stripe link)
    from pricing.yml so every page stays correct as pricing.yml updates."""
    skus = full_pricing.get("skus", full_pricing)

    audit = skus.get("audit", {})
    audit_tiers = {t.get("name"): t for t in audit.get("tiers", [])}
    standard = audit_tiers.get("standard", {})
    surge_30 = audit_tiers.get("surge_30d", {})
    surge_7 = audit_tiers.get("surge_7d", {})
    audit_base = standard.get("price_usd", 299)

    pack = skus.get("migration_pack", {})
    pack_base = pack.get("price_usd", 1499)

    return {
        "audit_pdf": {
            "base": audit_base,
            "link": standard.get("stripe_payment_link", f"{SITE_URL}/audit/"),
            "surge_30d_price": surge_30.get("price_usd", int(audit_base * 1.33)),
            "surge_30d_link": surge_30.get("stripe_payment_link", f"{SITE_URL}/audit/"),
            "surge_7d_price": surge_7.get("price_usd", audit_base * 2),
            "surge_7d_link": surge_7.get("stripe_payment_link", f"{SITE_URL}/audit/"),
        },
        "migration_pack": {
            "base": pack_base,
            "link": pack.get("stripe_payment_link", f"{SITE_URL}/pack/"),
        },
    }


def compute_urgency(dep, pricing_view):
    """Deterministic urgency + surge pricing derived ONLY from the cited
    deadline date in deprecations.yml and the tiers in pricing.yml."""
    days = get_days_until_deadline(dep["date"])
    audit = pricing_view["audit_pdf"]

    if days < 0:
        tier, label = "passed", "deadline passed"
        headline = (
            f"This deadline passed on {dep['date']}. "
            "Affected resources are now in the post-deadline window — clean up before the next enforcement phase."
        )
        audit_price, audit_link = audit["base"], audit["link"]
    elif days <= 7:
        tier, label = "urgent", "less than 7 days"
        headline = f"Only {days} days until the {dep['date']} deadline. This is the final week."
        audit_price, audit_link = audit["surge_7d_price"], audit["surge_7d_link"]
    elif days <= 30:
        tier, label = "soon", "within 30 days"
        headline = f"{days} days until the {dep['date']} deadline."
        audit_price, audit_link = audit["surge_30d_price"], audit["surge_30d_link"]
    else:
        tier, label = "ahead", "more than 30 days out"
        headline = f"{days} days until the {dep['date']} deadline — enough runway to migrate safely."
        audit_price, audit_link = audit["base"], audit["link"]

    return {
        "tier": tier,
        "label": label,
        "headline": headline,
        "days_until": days,
        "audit_price": audit_price,
        "audit_link": audit_link,
    }


def find_related(dep, all_deps, limit=4):
    """Internal-linking signal: deprecations sharing a kit or any tag.
    Deterministic ordering (by deadline date) so output is stable."""
    dep_tags = set(dep.get("tags", []))
    related = []
    for other in all_deps:
        if other["slug"] == dep["slug"]:
            continue
        same_kit = other.get("kit") and other.get("kit") == dep.get("kit")
        shared_tags = dep_tags & set(other.get("tags", []))
        if same_kit or shared_tags:
            related.append(other)
    related.sort(key=lambda d: d.get("date", "9999-99-99"))
    return related[:limit]


def build_migration_pages(deprecations, full_pricing):
    """Build SEO pages for each deprecation. Every fact is sourced from
    deprecations.yml (and carries its source_url), satisfying RULES.md by
    construction — zero LLM, deterministic."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )

    try:
        template = env.get_template("migrate.html.j2")
    except Exception:
        # Fallback if template doesn't exist
        return {}

    pricing_view = build_pricing_view(full_pricing)

    all_deps = deprecations.get("deprecations", [])
    for dep in all_deps:
        dep["slug"] = slugify(dep["name"])

    now_iso = datetime.now(UTC).isoformat()
    pages = {}
    for dep in all_deps:
        urgency = compute_urgency(dep, pricing_view)
        related = find_related(dep, all_deps)
        html = template.render(
            deprecation=dep,
            pricing=pricing_view,
            urgency=urgency,
            related=related,
            site_url=SITE_URL,
            now=now_iso,
        )
        pages[f"migrate/{dep['slug']}/index.html"] = html

    # Hub / index page that links every deprecation page (internal linking +
    # crawlable entry point referenced by every leaf page's breadcrumb).
    pages["migrate/index.html"] = build_migrate_index(all_deps, pricing_view, now_iso)

    return pages


def build_migrate_index(all_deps, pricing_view, now_iso):
    """Deterministic hub page listing every tracked AWS deprecation,
    ordered by deadline, with cited deadlines and severities."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    ordered = sorted(all_deps, key=lambda d: d.get("date", "9999-99-99"))
    rows = []
    for dep in ordered:
        urgency = compute_urgency(dep, pricing_view)
        rows.append(
            {
                **dep,
                "days_until": urgency["days_until"],
                "tier": urgency["tier"],
            }
        )
    try:
        template = env.get_template("migrate_index.html.j2")
    except Exception:
        return ""
    return template.render(
        deprecations=rows, site_url=SITE_URL, now=now_iso
    )


def build_sitemap(deprecations):
    """Build sitemap.xml."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )

    try:
        template = env.get_template("sitemap.xml.j2")
    except Exception:
        return None

    # Add slugs to deprecations
    for dep in deprecations.get("deprecations", []):
        dep["slug"] = slugify(dep["name"])

    return template.render(
        deprecations=deprecations.get("deprecations", []),
        now=datetime.now(UTC).strftime("%Y-%m-%d"),
    )


def build_llms_txt(deprecations, pricing_view):
    """Deterministic llms.txt (llmstxt.org) so AI search engines can cite
    EOLkits' deprecation facts. Every line is sourced from deprecations.yml
    and carries the primary source_url — no model output, cannot hallucinate."""
    all_deps = deprecations.get("deprecations", [])
    for dep in all_deps:
        dep["slug"] = slugify(dep["name"])
    ordered = sorted(all_deps, key=lambda d: d.get("date", "9999-99-99"))

    lines = [
        "# EOLkits",
        "",
        "> Deterministic, CI-citation-gated CLIs and migration services for AWS "
        "platform deprecation deadlines (Lambda runtimes, Amazon Linux 2, IMDSv1). "
        "Every fact below is sourced from a primary AWS or upstream document.",
        "",
        "## AWS deprecation deadlines",
        "",
    ]
    for dep in ordered:
        page = f"{SITE_URL}/migrate/{dep['slug']}/"
        lines.append(
            f"- [{dep['name']}]({page}): deadline {dep['date']}, "
            f"severity {dep.get('severity', 'n/a')}, service {dep.get('service', 'n/a')}. "
            f"Source: {dep.get('url', '')}"
        )
    lines += [
        "",
        "## Pricing",
        "",
        f"- Free CLI: MIT-licensed kits (al2023-gate, python-pivot, lambda-lifeline). "
        f"git clone https://github.com/ntoledo319/EOLkits",
        f"- [Audit PDF]({SITE_URL}/audit/): ${pricing_view['audit_pdf']['base']} "
        f"(surges to ${pricing_view['audit_pdf']['surge_30d_price']} within 30 days, "
        f"${pricing_view['audit_pdf']['surge_7d_price']} within 7 days) — "
        f"hash-anchored deterministic finding report.",
        f"- [Migration Pack]({SITE_URL}/pack/): "
        f"${pricing_view['migration_pack']['base']:,} — automated PR with codemods + "
        f"IaC patches + canary plan + rollback; auto-refund if CI fails within 7 days.",
        "",
        "## Calendar",
        "",
        f"- [Deadline calendar (.ics)]({SITE_URL}/deprecations.ics): subscribe to "
        f"every tracked AWS deprecation deadline.",
        "",
    ]
    return "\n".join(lines) + "\n"


def build_robots_txt():
    """robots.txt pointing crawlers at the sitemap and llms.txt."""
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )


def build_verify_page():
    """Build the verification page."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )

    try:
        template = env.get_template("verify.html.j2")
        return template.render()
    except Exception:
        return None


def build_index_page(pricing):
    """Rebuild the main index.html with dynamic pricing."""
    index_path = DOCS_DIR / "index.html"
    if index_path.exists():
        with open(index_path) as f:
            return f.read()
    return ""


def build_partners_page():
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Partners — EOLkits</title>
<style>body{font-family:system-ui,sans-serif;max-width:780px;margin:0 auto;padding:2rem;line-height:1.6}.brand{color:#2563eb;font-weight:600}.box{border:1px solid #e5e7eb;border-radius:8px;padding:1.5rem;margin:1.25rem 0;background:#f9fafb}button{background:#2563eb;color:#fff;border:0;padding:.7rem 1.4rem;border-radius:6px;cursor:pointer}</style>
</head><body><a href="/" class="brand">← EOLkits</a><h1>White-label Partners</h1>
<p>Run EOLkits audits under your brand. 70% revenue share. Stripe Connect handles the split automatically — no invoicing, no reconciliation.</p>
<div class="box"><h3>How it works</h3>
<ol><li>Sign up with your business email and domain.</li>
<li>Add a DNS TXT record we provide to verify domain ownership (anti-impersonation).</li>
<li>Stripe Connect Express onboarding (one-time, ~3 minutes, handled by Stripe).</li>
<li>Call <code>POST /partners/&lt;your-slug&gt;/audit</code> from your tooling. We deliver a co-branded PDF and split the payment 70/30.</li></ol></div>
<form action="https://eolkits-worker.eolkits-kits.workers.dev/partners/signup" method="POST">
<p><input type="email" name="email" placeholder="contact@yourcompany.com" required style="padding:.5rem;width:300px"></p>
<p><input type="text" name="display_name" placeholder="Display name" required style="padding:.5rem;width:300px"></p>
<p><input type="text" name="domain" placeholder="yourcompany.com" required style="padding:.5rem;width:300px"></p>
<button type="submit">Start partner signup</button></form>
<footer style="margin-top:3rem;color:#6b7280;font-size:.85rem"><a href="/">Home</a> · <a href="/legal/terms">Terms</a></footer></body></html>"""


def build_status_page():
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Status — EOLkits</title>
<style>body{font-family:system-ui,sans-serif;max-width:900px;margin:0 auto;padding:2rem;line-height:1.6}.brand{color:#2563eb;font-weight:600}.svc{display:flex;justify-content:space-between;align-items:center;border:1px solid #e5e7eb;border-radius:8px;padding:1rem;margin:.5rem 0}.dot{width:12px;height:12px;border-radius:50%;display:inline-block;margin-right:8px;background:#9ca3af}.dot.green{background:#10b981}.dot.red{background:#ef4444}.muted{color:#6b7280;font-size:.85rem}</style>
</head><body><a href="/" class="brand">← EOLkits</a><h1>System Status</h1>
<p class="muted">Synthetic checks every 5 minutes. Data pulled from <a href="/status/data.json">/status/data.json</a>.</p>
<div id="services"><div class="svc"><span><span class="dot" id="dot-stripe"></span>Stripe checkout</span><span id="t-stripe">—</span></div>
<div class="svc"><span><span class="dot" id="dot-worker"></span>Worker API</span><span id="t-worker">—</span></div>
<div class="svc"><span><span class="dot" id="dot-runner"></span>Job runner</span><span id="t-runner">—</span></div>
<div class="svc"><span><span class="dot" id="dot-email"></span>Email delivery</span><span id="t-email">—</span></div>
<div class="svc"><span><span class="dot" id="dot-github"></span>GitHub App</span><span id="t-github">—</span></div></div>
<h2>Throughput (last 7 days)</h2>
<ul id="metrics"><li>Loading…</li></ul>
<script>
fetch('/status/data.json').then(r=>r.json()).then(d=>{
  for(const s of ['stripe','worker','runner','email','github']){
    const v=(d.checks||{})[s];
    if(v){document.getElementById('dot-'+s).className='dot '+(v.ok?'green':'red');document.getElementById('t-'+s).textContent=v.last_checked||'';}
  }
  const m=document.getElementById('metrics');m.innerHTML='';
  for(const [k,v] of Object.entries(d.metrics||{})){const li=document.createElement('li');li.textContent=k+': '+v;m.appendChild(li);}
}).catch(()=>{document.getElementById('metrics').innerHTML='<li>status feed unavailable</li>';});
</script>
<footer style="margin-top:3rem;color:#6b7280;font-size:.85rem"><a href="/">Home</a></footer></body></html>"""


def build_status_data_seed():
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return json.dumps(
        {
            "generated_at": now,
            "checks": {
                "stripe": {"ok": True, "last_checked": now},
                "worker": {"ok": True, "last_checked": now},
                "runner": {"ok": True, "last_checked": now},
                "email": {"ok": True, "last_checked": now},
                "github": {"ok": True, "last_checked": now},
            },
            "metrics": {
                "audits_delivered_7d": 0,
                "prs_opened_7d": 0,
                "drift_watch_subscribers": 0,
                "rules_in_public_pack": 0,
            },
        },
        indent=2,
    )


def build_blog_index():
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Blog — EOLkits</title>
<style>body{font-family:system-ui,sans-serif;max-width:780px;margin:0 auto;padding:2rem;line-height:1.6}.brand{color:#2563eb;font-weight:600}article{border-bottom:1px solid #e5e7eb;padding:1rem 0}time{color:#6b7280;font-size:.85rem}</style>
</head><body><a href="/" class="brand">← EOLkits</a><h1>Operations log</h1>
<p>Auto-published every week from CI. <a href="/blog/feed.xml">RSS</a></p>
<article><time>—</time><h2>Welcome</h2><p>This log is generated weekly by <code>.github/workflows/blog-loop.yml</code>. The first real entry lands after the next CI run.</p></article>
<footer style="margin-top:3rem;color:#6b7280;font-size:.85rem"><a href="/">Home</a></footer></body></html>"""


def build_vs_index(competitors):
    items = "".join(
        f'<li><a href="/vs/{slugify(c["name"])}/">EOLkits vs {c["name"]}</a> <span style="color:#6b7280">— {c["category"]}</span></li>'
        for c in competitors
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Comparisons — EOLkits</title>
<style>body{{font-family:system-ui,sans-serif;max-width:780px;margin:0 auto;padding:2rem;line-height:1.6}}.brand{{color:#2563eb;font-weight:600}}</style>
</head><body><a href="/" class="brand">← EOLkits</a><h1>EOLkits vs alternatives</h1>
<p>Factual comparisons updated nightly from public sources. No logos used. Plain-text product names under nominative fair use.</p>
<ul>{items}</ul>
<p style="color:#6b7280;font-size:.85rem">Pages reflect public data as of the timestamp shown on each page. If a fact is wrong or outdated, open an issue.</p>
<footer style="margin-top:3rem;color:#6b7280;font-size:.85rem"><a href="/">Home</a></footer></body></html>"""


def build_vs_page(competitor):
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EOLkits vs {competitor["name"]} — comparison</title>
<meta name="description" content="Factual comparison of EOLkits and {competitor["name"]} for AWS deprecation migrations. As of {today}.">
<link rel="canonical" href="https://ntoledo319.github.io/EOLkits/vs/{slugify(competitor["name"])}/">
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:0 auto;padding:2rem;line-height:1.6}}.brand{{color:#2563eb;font-weight:600}}table{{width:100%;border-collapse:collapse;margin:1rem 0}}th,td{{border:1px solid #e5e7eb;padding:.6rem;text-align:left}}th{{background:#f9fafb}}.muted{{color:#6b7280;font-size:.85rem}}</style>
</head><body><a href="/" class="brand">← EOLkits</a><h1>EOLkits vs {competitor["name"]}</h1>
<p class="muted">Category: {competitor["category"]}. Source: <a href="{competitor["url"]}" rel="nofollow">{competitor["url"]}</a>. As of {today}.</p>
<table><tr><th>Capability</th><th>EOLkits</th><th>{competitor["name"]}</th></tr>
<tr><td>License</td><td>MIT (open core)</td><td>{competitor.get("license", "—")}</td></tr>
<tr><td>Codemod / source rewriting</td><td>Yes</td><td>{competitor.get("codemod", "—")}</td></tr>
<tr><td>IaC patching (SAM/CDK/TF)</td><td>Yes</td><td>{competitor.get("iac", "—")}</td></tr>
<tr><td>Canary deploy + rollback</td><td>Yes</td><td>{competitor.get("canary", "—")}</td></tr>
<tr><td>Determinism (CI-gated)</td><td>Yes</td><td>{competitor.get("deterministic", "—")}</td></tr>
<tr><td>Hash-anchored audit reports</td><td>Yes</td><td>{competitor.get("hash_anchored", "—")}</td></tr>
<tr><td>Pricing</td><td>Free CLI; Audit $299; Pack $1,499</td><td>{competitor.get("pricing", "—")}</td></tr></table>
<p class="muted">Trademark notice: "{competitor["name"]}" is referenced in plain text under nominative fair use. No logos are used. If you operate this product and a fact above is wrong, please open an issue at <a href="https://github.com/ntoledo319/EOLkits/issues">github.com/ntoledo319/EOLkits/issues</a> and we will correct within 24h of confirmation.</p>
<footer style="margin-top:3rem;color:#6b7280;font-size:.85rem"><a href="/">Home</a> · <a href="/vs/">All comparisons</a></footer></body></html>"""


COMPETITORS = [
    {
        "name": "CloudQuery",
        "category": "Cloud asset inventory",
        "url": "https://www.cloudquery.io/",
        "license": "Apache-2.0",
        "codemod": "No",
        "iac": "No (read-only)",
        "canary": "No",
        "deterministic": "n/a",
        "hash_anchored": "No",
        "pricing": "Free + paid SaaS",
    },
    {
        "name": "HeroDevs",
        "category": "Post-EOL support subscription",
        "url": "https://www.herodevs.com/",
        "license": "Proprietary",
        "codemod": "No",
        "iac": "No",
        "canary": "No",
        "deterministic": "n/a",
        "hash_anchored": "No",
        "pricing": "Enterprise quote",
    },
    {
        "name": "aws-samples runtime-update-helper",
        "category": "AWS sample script",
        "url": "https://github.com/aws-samples/aws-lambda-runtime-update-helper",
        "license": "MIT-0",
        "codemod": "No",
        "iac": "No (runtime field flip only)",
        "canary": "No",
        "deterministic": "Unspecified",
        "hash_anchored": "No",
        "pricing": "Free",
    },
]


def build_deprecations_ics(deprecations):
    """RFC 5545 calendar feed."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//EOLkits//AWS Deprecations//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:AWS Deprecation Deadlines (EOLkits)",
        "X-WR-TIMEZONE:UTC",
    ]
    for dep in deprecations.get("deprecations", []):
        try:
            d = datetime.strptime(dep["date"], "%Y-%m-%d")
        except Exception:
            continue
        dtstart = d.strftime("%Y%m%d")
        dtend = (d + timedelta(days=1)).strftime("%Y%m%d")
        uid = f"{slugify(dep['name'])}@eolkits"
        summary = dep["name"].replace(",", "\\,")
        desc_raw = dep.get("description", "") + f" Source: {dep.get('url','')}"
        desc = desc_raw.replace("\\", "\\\\").replace(",", "\\,").replace("\n", "\\n")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;VALUE=DATE:{dtstart}",
            f"DTEND;VALUE=DATE:{dtend}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            f"URL:{dep.get('url','')}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\n".join(lines) + "\n"


def main():
    """Main build entry point."""
    print("EOLkits Static Site Builder")
    print("=" * 40)

    # Load configuration
    pricing = load_pricing()
    print(f"Loaded {len(pricing['skus'])} SKUs from pricing.yml")

    # Ensure docs directory exists
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # Load deprecations
    deprecations = load_deprecations()
    print(f"Loaded {len(deprecations.get('deprecations', []))} deprecations")

    # Build pages
    pages = {
        "index.html": build_index_page(pricing),
        "audit/index.html": build_audit_page(pricing),
        "pack/index.html": build_pack_page(pricing),
        "license/index.html": build_license_page(pricing),
        "partners/index.html": build_partners_page(),
        "status/index.html": build_status_page(),
        "status/data.json": build_status_data_seed(),
        "blog/index.html": build_blog_index(),
        "vs/index.html": build_vs_index(COMPETITORS),
        "deprecations.ics": build_deprecations_ics(deprecations),
    }
    # widget.js lives at docs/widget.js (canonical). If a legacy source still
    # exists at apps/widget/embed.js, fall back to it the first time we build.
    if not (DOCS_DIR / "widget.js").exists():
        widget_src = BASE_DIR.parent / "widget" / "embed.js"
        if widget_src.exists():
            pages["widget.js"] = widget_src.read_text()

    for c in COMPETITORS:
        pages[f"vs/{slugify(c['name'])}/index.html"] = build_vs_page(c)

    # Build migration pages
    migration_pages = build_migration_pages(deprecations, pricing)
    pages.update(migration_pages)

    # Build sitemap
    sitemap = build_sitemap(deprecations)
    if sitemap:
        pages["sitemap.xml"] = sitemap

    # Build verification page
    verify_page = build_verify_page()
    if verify_page:
        pages["verify/index.html"] = verify_page

    # AI-search + crawler discovery, deterministic from the cited YAML
    pricing_view = build_pricing_view(pricing)
    pages["llms.txt"] = build_llms_txt(deprecations, pricing_view)
    pages["robots.txt"] = build_robots_txt()

    for path, content in pages.items():
        full_path = DOCS_DIR / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w") as f:
            f.write(normalize_project_links(content))
        print(f"Built: docs/{path}")

    # Copy legal docs
    legal_dir = DOCS_DIR.parent / "legal"
    legal_output = DOCS_DIR / "legal"
    if legal_dir.exists():
        legal_output.mkdir(exist_ok=True)
        for legal_file in legal_dir.glob("*.md"):
            # Convert markdown to HTML (simple version)
            import shutil

            output = legal_output / legal_file.with_suffix(".html").name
            shutil.copy(legal_file, output)
            print(f"Copied: legal/{legal_file.name}")
        security_file = DOCS_DIR.parent / "SECURITY.md"
        if security_file.exists():
            import shutil

            shutil.copy(security_file, legal_output / "SECURITY.html")
            print("Copied: SECURITY.md")

    print("=" * 40)
    print("Build complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
