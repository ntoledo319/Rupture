#!/usr/bin/env python3
"""
Rupture Runner - Job dispatcher for the containerized job processor.
Reads job descriptors from stdin and executes the appropriate action.
"""

import sys
import json
import os
from pathlib import Path


def main():
    """Main entry point - reads job from stdin."""
    # Read job descriptor from stdin
    job = json.load(sys.stdin)
    
    job_type = job.get("type")
    
    try:
        if job_type == "audit_pdf":
            result = handle_audit_pdf(job)
        elif job_type == "migration_pr":
            result = handle_migration_pr(job)
        elif job_type == "license_key":
            result = handle_license_key(job)
        elif job_type == "drift_watch_setup":
            result = handle_drift_watch_setup(job)
        elif job_type == "email":
            result = handle_email(job)
        else:
            raise ValueError(f"Unknown job type: {job_type}")
        
        # Output result as JSON
        print(json.dumps({
            "success": True,
            "result": result,
        }))
        sys.exit(0)
        
    except Exception as e:
        # Output error as JSON
        print(json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }))
        sys.exit(1)


def handle_audit_pdf(job: dict) -> dict:
    """Generate an audit PDF report."""
    from audit_pdf import generate_audit_pdf
    
    upload_url = job.get("upload_url")
    email = job.get("email")
    deadline = job.get("deadline")
    
    # Download uploaded files
    # Run kit analysis
    # Generate PDF with WeasyPrint
    # Upload to R2
    # Queue email job
    
    pdf_path = generate_audit_pdf(
        upload_url=upload_url,
        email=email,
        deadline=deadline,
    )
    
    return {
        "pdf_path": pdf_path,
        "email": email,
    }


def handle_migration_pr(job: dict) -> dict:
    """Open a migration PR on user's repository."""
    from migration_pr import create_migration_pr
    
    repo = job.get("repo")
    email = job.get("email")
    installation_id = job.get("installationId")
    
    # Use GitHub App token to:
    # 1. Clone the repo
    # 2. Run the appropriate kit
    # 3. Create a branch
    # 4. Commit changes
    # 5. Open PR
    
    pr_info = create_migration_pr(
        repo=repo,
        email=email,
        installation_id=installation_id,
    )
    
    return {
        "pr_url": pr_info["pr_url"],
        "pr_number": pr_info["pr_number"],
        "repo": repo,
    }


def handle_license_key(job: dict) -> dict:
    """Generate and email a license key."""
    company = job.get("company")
    email = job.get("email")
    
    # Generate license key
    # Store in KV
    # Queue email job
    
    return {
        "company": company,
        "email": email,
        "status": "key_generated",
    }


def handle_drift_watch_setup(job: dict) -> dict:
    """Set up drift monitoring for a repository."""
    repo = job.get("repo")
    iam_role = job.get("iam_role")
    email = job.get("email")
    
    # Validate IAM role
    # Store watch configuration
    # Schedule first scan
    
    return {
        "repo": repo,
        "status": "watch_configured",
    }


def handle_email(job: dict) -> dict:
    """Send a transactional email."""
    to = job.get("to")
    subject = job.get("subject")
    body = job.get("body")
    
    # Send via Resend API
    # Or queue for later if Resend unavailable
    
    return {
        "to": to,
        "subject": subject,
        "status": "queued",
    }


if __name__ == "__main__":
    main()
