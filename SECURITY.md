# Security and data handling

Use this reference workbench locally through the printed 127.0.0.1 URL. Do not expose
the Python HTTP server to a public network. Host and Origin checks mitigate browser
cross-origin access; this is not an authenticated multi-user service.

Uploads stay in server memory and are not logged or persisted by the application.
Downloaded reports contain record identifiers and business values. Input hashes
are provenance, not anonymization. Only synthetic fixtures belong in this repo.
CSV string cells are neutralized against common spreadsheet-formula prefixes.
The UI renders supplied text using textContent rather than HTML insertion.

For a vulnerability, use GitHub private reporting if available; otherwise contact
the maintainer through their public profile without publishing sensitive examples.
Do not attach real statements, invoices, credentials or personal data to issues.

## Supported version
Security fixes target the current main branch (1.x). This is a local portfolio
application, not an Internet-facing or authenticated enterprise service.

## Responsible report
Provide affected file/version, a synthetic reproduction, expected impact and any
suggested mitigation. Do not publish an exploit containing customer data or live
credentials. Private reporting, when enabled, is available at:
https://github.com/muratmiracg-dev/financial-reconciliation-controls-engine/security/advisories/new
No response-time SLA is promised for this personally maintained project.

## Supply-chain controls
GitHub Actions use full commit pins; CI has read-only repository permissions.
Checkout credentials are not persisted. Only CodeQL jobs may write security events.
Dependabot proposals require review; there is no automatic merge or deployment.
CODEOWNERS alone does not enforce approval. Repository settings control enforcement.

## Threat model and residual risk
Untrusted CSVs may contain invalid data or spreadsheet formulas. Input bounds,
schema checks and formula-prefix escaping reduce these risks. The server is local,
but large candidate sets can still consume CPU and memory. Other processes running
as the same user can access local files or services. Browser/server memory is not
securely erased, and exported reports may contain sensitive values. Do not use this
reference service as a multi-user production endpoint.
