# Matching methodology and boundaries

## Scope
Cash-settlement reconciliation for a single reporting entity. Invoice amounts are
**open amounts at the start of the supplied window**, not necessarily original invoice
face values. Positive means cash receivable/inflow; negative means payable/outflow.
All inputs must cover compatible periods and the same entity. No FX conversion,
VAT calculation, ERP posting, bank connection or legal compliance certification.

## Order of operations
1. Validate exact CSV schemas, unique IDs, ISO dates, finite two-decimal amounts.
2. Quarantine suspected business duplicates; retain both records as evidence.
3. Check each journal entry balances separately in every currency.
4. Compare linked `BANK` ledger debit-minus-credit to each bank movement, exactly.
5. Form connected components using explicit invoice references. A bank reference
   lists invoice IDs separated by semicolons. Components support 1:1, N:1, 1:N and
   N:M totals. This is group-level reconciliation, not an inferred allocation matrix.
6. Apply currency, party, sign, duplicate, ledger and pairwise date-window controls.
7. Accept a group as `MATCHED` only with explicit references and no failed checks.
8. Suggest unreferenced 1:1 candidates only when amount, party, currency and date
   agree and the match is unique in both directions. These always remain `REVIEW`.
9. Report unused banks, open invoices, ambiguity and ledger exceptions separately.

`MATCHED` is analytical status, never accounting approval. No records are posted.
A missing invoice reference never falls through into speculative automatic matching.
No combinatorial subset-sum guessing is used for unreferenced split/batch payments.

## Arithmetic and evidence
Amounts are parsed with Decimal and stored as integer minor units. JSON and CSV
exports use minor units (112500 = TRY 1,125.00); the UI formats major units.
Currency totals never combine different currencies. Mixed-currency components
have null amounts/differences. Gross unresolved exposure is the sum of absolute
bank amounts not in matched groups; it is not a loss estimate or invoice balance.
Signed difference = bank cash - invoice open amount. A partial payment remains a
review group; it does not silently reduce or close the invoice in an ERP.

Default tolerance is one minor unit, maximum 100. Date window is symmetric
absolute calendar-day difference, default 45, maximum 365. Every bank/invoice pair
within a referenced component must be within the window. This conservative rule
may flag long-running installments. BANK ledger lines also use this window.

A FEE debit explaining an inflow shortfall adds a reason code, but never silently
clears the difference. Fee detection is illustrative and does not classify every
possible outgoing-payment fee arrangement.

## Rule strength, not probability
Reference groups receive evidence strength 100 for explicit linkage, even if other
controls fail. Unreferenced suggestions score 70 + 20 × description similarity
(rounded). Description similarity uses a deterministic sequence comparison.
Scores are not calibrated likelihoods and must not override control flags.

## Reproducibility and audit
Run identity hashes the engine version, raw UTF-8 CSV inputs and policy. Changing
whitespace can change the run ID. The JSON stores input hashes, policy, all groups
and exceptions; it is reproducibility evidence, not an immutable regulated audit
log. No approval state is persisted. JSON contains user-supplied identifiers.

## Limits
10,000 rows per input, 500 characters per field; browser uploads 2 MB per file,
API total 8 MB. This is a local reference application for small extracts; candidate
matching can be quadratic. Duplicate detection flags identical business fields,
not all semantic duplicates or fraud. A balanced entry can still be misclassified.
BANK/AR/FEE are normalized account roles, not a national chart of accounts.
