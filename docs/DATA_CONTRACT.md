# Input contract

UTF-8 comma-separated CSV, header required. Column order may vary; no extra columns.
Quoted descriptions may contain commas. IDs are case-sensitive. Party values must
be normalized upstream; exact equality is intentional. Dates: YYYY-MM-DD.
Currencies: TRY, USD, EUR, GBP (all supported with two decimal places).
Amounts use decimal points, no thousands separator, no more than two decimal places.
Empty files must still contain the header. Inputs are for one reporting entity.

| File | Required columns |
|---|---|
| bank.csv | id,date,party,currency,amount,reference,description |
| invoices.csv | id,date,party,currency,amount,description |
| journal.csv | id,entry_id,date,bank_id,account,currency,debit,credit |

Bank `reference`: invoice IDs separated by `;`, or empty. `amount` is signed net
cash. Invoice `amount` is signed open balance at window start. Both are nonzero.
Journal `id` identifies a line; `entry_id` groups a balanced posting. `bank_id` links
to bank id (can be empty for unrelated lines). `account=BANK` identifies the cash
side; `FEE` identifies fee expense; other role names are accepted. Debit and credit
must be nonnegative and not both positive on one line. A journal entry must balance
within each currency. All linked BANK lines together must equal the movement.

## Example
A 10,000 receivable collected net of a 25 fee:
- Invoice open amount: 10000.00
- Bank inflow: 9975.00, with invoice reference
- Journal: BANK debit 9975; FEE debit 25; AR credit 10000

Result: `REVIEW`, amount difference -2500 minor units, fee explanation present.
Download the three example files from the app, or use `data/demo/`.
The benchmark truth file is for validation only and is never passed to the engine.
# Journal posting-date invariant

Every line belonging to the same journal `entry_id` must have one identical
ISO posting date. A cross-date entry is reported as `ENTRY_DATE_CONFLICT`,
quarantined from reconciliation, and cannot support an automatic match even
when its debits and credits balance.
