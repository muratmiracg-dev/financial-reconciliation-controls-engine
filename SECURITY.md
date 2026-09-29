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
