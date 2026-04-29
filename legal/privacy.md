# Privacy Policy — Rupture

**Last updated:** April 29, 2026

## 1. Introduction

This Privacy Policy explains how Rupture ("we", "us", "our") collects, uses, and protects your information when you use our services.

## 2. Information We Collect

### 2.1 Automatically Collected
- **Usage data:** Page views, feature usage, error logs
- **Technical data:** IP address, browser type, operating system
- **Purchase data:** Stripe checkout session metadata (no full card details)

### 2.2 Provided by You
- **Account information:** Email address (for purchase receipts)
- **Repository information:** When using Migration Pack (repo names, PR metadata)
- **Audit uploads:** Files uploaded for analysis (stored temporarily, see Section 4)

### 2.3 From Third Parties
- **Stripe:** Payment confirmation, customer ID
- **GitHub:** Repository metadata (with your permission via GitHub App)
- **Resend:** Email delivery status

## 3. How We Use Information

| Purpose | Data Used | Legal Basis |
|---------|-----------|-------------|
| Provide Services | Purchase data, uploads | Contract fulfillment |
| Process Payments | Stripe data | Contract fulfillment |
| Deliver Reports | Email address | Contract fulfillment |
| Improve Services | Usage data, error logs | Legitimate interest |
| Legal Compliance | All data | Legal obligation |

## 4. Data Storage and Retention

### 4.1 Uploaded Files (Audit Analysis)
- Stored in Cloudflare R2 (encrypted at rest)
- **Retention:** 30 days maximum
- **Auto-deletion:** Files deleted after report delivery + 30 days
- **Access:** Only accessible via unique, unguessable URL

### 4.2 Purchase Records
- Retained for 7 years (tax/accounting requirements)
- Stored in Stripe (PCI-compliant)

### 4.3 Repository Metadata
- Stored only while GitHub App is installed
- Deleted upon uninstall

## 5. Data Sharing

We do **not** sell your data. We share data only with:

| Recipient | Purpose | Data Shared |
|-----------|---------|-------------|
| Stripe | Payment processing | Payment intent, email |
| Cloudflare | Infrastructure | Uploaded files (encrypted) |
| GitHub | PR creation | Repository access (your permission) |
| Resend | Email delivery | Email address, message content |

All recipients are GDPR-compliant and under data processing agreements where required.

## 6. Cookies and Tracking

- **Essential cookies:** Required for site functionality
- **Analytics:** Minimal, privacy-preserving analytics (no third-party trackers)
- **No advertising cookies**

## 7. Your Rights

Under GDPR and similar regulations, you have the right to:
- **Access:** Request a copy of your data
- **Correction:** Update inaccurate information
- **Deletion:** Request data deletion (subject to legal retention)
- **Portability:** Receive data in machine-readable format
- **Objection:** Object to certain processing

To exercise these rights:
- GitHub Discussions: https://github.com/ntoledo319/Rupture/discussions
- Include "Privacy Request" in subject

## 8. Security Measures

- All data encrypted in transit (TLS 1.3)
- Uploaded files encrypted at rest (AES-256)
- Stripe handles all payment data (PCI DSS Level 1)
- Regular security audits via automated CI
- No plaintext credential storage

## 9. International Transfers

Data may be processed in:
- United States (Cloudflare, Stripe, GitHub, Resend)
- European Union (optional, via Cloudflare EU regions)

All providers offer adequate protection under GDPR adequacy decisions or Standard Contractual Clauses.

## 10. Children's Privacy

Our services are not intended for users under 16. We do not knowingly collect data from children.

## 11. Changes to This Policy

We will notify users of significant changes via:
- GitHub repository notice
- Email to registered users

## 12. Contact Information

For privacy questions or requests:
- GitHub Discussions: https://github.com/ntoledo319/Rupture/discussions
- Privacy-specific: Open a discussion with "[Privacy]" prefix

## 13. Data Protection Officer

Currently: The project operator (contact via GitHub Discussions)
To be formalized upon business entity registration.

---

*This Privacy Policy is adapted from the Mozilla Privacy Policy template and customized for Rupture's specific data practices.*
