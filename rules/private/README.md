# Private Rule Packs (Org License)

This directory contains private rule packs available exclusively to Organization License holders.

## Structure

```
rules/private/
├── custom/
│   └── README.md          # Guide for creating custom rules
├── enterprise/
│   └── # Premium rules for common enterprise patterns
└── README.md              # This file
```

## Custom Rules

Org License holders can define private rules specific to their infrastructure:

```yaml
# rules/private/acme-corp/internal-apis.yml
rules:
  - name: "Internal API v1 Deprecation"
    pattern: "api\.internal\.acme\.com/v1"
    replacement: "api.internal.acme.com/v2"
    severity: high
    message: "Internal API v1 will be shut down on 2026-06-01"
```

## Enterprise Rules

Common enterprise patterns available to all Org License holders:

- `legacy-auth.yml` - Detect deprecated authentication mechanisms
- `internal-framework.yml` - Rules for company-specific frameworks
- `compliance-gaps.yml` - Detect patterns that violate internal compliance

## License

Private rule packs are **NOT** MIT licensed. They are provided under the Organization License terms.

See `/legal/terms` for details.
