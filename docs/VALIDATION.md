# Validation evidence

## Automated checks
`python -m unittest discover -s tests -v`

52 tests cover controlled fixture statuses and invoice allocations, record non-reuse, deterministic results,
split and batch settlements, valid and detached fee evidence, multi-currency isolation, party/date
conflicts, exact cents, invalid amounts/dates/schemas/IDs, unbalanced ledger,
reference-free suggestions, ambiguity, unknown references, policy limits, formula
escaping, empty extracts, tolerance, outgoing payments, HTTP requests and
cross-origin/host rejection.

The committed `artifacts/report.json` and `artifacts/benchmark.json` are regenerated
in CI and compared byte for byte. The engine has no third-party Python runtime dependencies.

## Benchmark design
53 bank movements, 53 invoices, 105 journal lines. The demo generator emits, for
every bank movement, the expected status and the exact invoice set it settles,
independently of the matching output. Truth labels are not passed to the matcher.
`artifacts/benchmark.json` scores both: a movement counts as correct only when its
status matches and it is grouped with exactly the expected invoices, so a payment
allocated to the wrong invoice no longer passes on status alone. 53/53 statuses and
53/53 allocations agree with the deterministic run, and CI regenerates and compares
the benchmark file byte for byte.
This measures regression consistency on an authored fixture; it is not a held-out
real-world performance estimate. Match precision/recall on real operational data
has not been measured. External validation is required before operational use.

## Known analytical limits
- Exact party identity must be normalized upstream.
- Near-duplicates with altered descriptions can evade duplicate detection.
- References can be wrong; even exact matches require operational review.
- Journal balance and amount agreement do not prove correct account classification.
- A period extract can omit earlier/later settlements and produce apparent open items.
- No exchange-rate, tax, reversal-chain or bank-specific format inference.
- No durable reviewer workflow, signed audit chain or multi-user permissions.

## UI verification boundary
JavaScript syntax validation passed. HTTP integration tests passed. A Playwright
visual/upload/download smoke-test script is included at tests/browser-smoke.cjs,
but could not be executed in the authoring environment because Chromium download
failed. No screenshot or browser-test success is claimed. Run it after installing
Playwright and Chromium, with python app.py running on port 8765.
