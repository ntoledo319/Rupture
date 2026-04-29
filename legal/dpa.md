# Data Processing Agreement (DPA)

**Last updated:** April 29, 2026

This Data Processing Agreement ("DPA") forms part of the Terms of Service between Rupture ("Processor") and the user ("Controller") for services involving personal data processing.

## 1. Definitions

- **"Controller"** means you, the user/organization using our services
- **"Processor"** means Rupture, processing data on your behalf
- **"Personal Data"** means any information relating to an identified or identifiable natural person
- **"Processing"** means any operation performed on Personal Data
- **"GDPR"** means EU General Data Protection Regulation 2016/679

## 2. Processing Details

### 2.1 Subject Matter
Automated migration analysis and reporting services for AWS infrastructure.

### 2.2 Duration
Processing occurs for the duration of:
- Active subscriptions
- File analysis (up to 30 days post-upload)
- Legal retention periods (7 years for financial records)

### 2.3 Nature and Purpose
- Analysis of infrastructure configurations
- Generation of migration reports
- Automated pull request creation
- Email delivery of reports

### 2.4 Types of Personal Data
- Email addresses
- Repository metadata (owner names, committer info)
- Infrastructure configuration data (may contain identifiers)

### 2.5 Categories of Data Subjects
- Your employees/contractors (if identifiable in metadata)
- End-users (indirectly, via infrastructure logs)

## 3. Processor Obligations

### 3.1 Processing Instructions
Processor shall process Personal Data only:
- In accordance with documented instructions from Controller
- As required by applicable law (in which case, Processor will notify Controller)
- For the purposes specified in Section 2

### 3.2 Confidentiality
All personnel with access to Personal Data are bound by confidentiality obligations.

### 3.3 Security Measures
Processor implements:
- Encryption in transit (TLS 1.3)
- Encryption at rest (AES-256)
- Access controls and authentication
- Regular security testing
- Incident response procedures

### 3.4 Subprocessors
Current subprocessors:

| Subprocessor | Service | Location |
|-------------|---------|----------|
| Stripe, Inc. | Payment processing | USA |
| Cloudflare, Inc. | Infrastructure | USA/EU |
| GitHub, Inc. | Code repository services | USA |
| Resend, Inc. | Email delivery | USA |

Processor may engage additional subprocessors with 30 days notice.

### 3.5 Data Subject Rights
Processor shall assist Controller in responding to data subject requests, including:
- Access requests
- Rectification requests
- Erasure requests
- Portability requests

### 3.6 Security Breach Notification
Processor shall notify Controller within 24 hours of becoming aware of any Personal Data breach.

### 3.7 Data Deletion
Upon service termination or expiry:
- Uploaded files deleted within 30 days
- Metadata deleted within 90 days
- Financial records retained per legal requirements

## 4. Controller Obligations

Controller shall:
- Ensure lawful basis for processing
- Provide accurate processing instructions
- Notify Processor of any data subject requests
- Obtain necessary consents/authorizations

## 5. Data Transfers

### 5.1 International Transfers
Personal Data may be transferred to countries outside the EEA. Such transfers are protected by:
- Standard Contractual Clauses (where applicable)
- Adequacy decisions (for approved countries)
- Binding corporate rules (where applicable)

### 5.2 Transfer Safeguards
All subprocessors listed in 3.4 participate in the EU-US Data Privacy Framework or have Standard Contractual Clauses in place.

## 6. Audit Rights

Controller may request audit of Processor's compliance with this DPA:
- Once per year (free)
- Additional audits at Controller's expense
- Subject to reasonable confidentiality requirements

## 7. Termination

Upon termination:
- Processor shall cease processing (except as required by law)
- Return or delete Personal Data per Controller's instruction
- Provide certification of deletion

## 8. Limitation of Liability

Each party's liability under this DPA is subject to the limitations in the main Terms of Service.

## 9. Governing Law

This DPA is governed by the law specified in the main Terms of Service.

## 10. Contact

For DPA-related inquiries:
- GitHub Discussions: https://github.com/ntoledo319/Rupture/discussions
- Include "DPA" in the discussion title

---

*This DPA is adapted from the GDPR.eu Data Processing Agreement template.*
