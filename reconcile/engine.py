"""Deterministic, review-only three-way cash reconciliation. Integer minor units."""

import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

VERSION = "1.0.0"
SCHEMAS = {
    "bank": ("id", "date", "party", "currency", "amount", "reference", "description"),
    "invoices": ("id", "date", "party", "currency", "amount", "description"),
    "journal": (
        "id",
        "entry_id",
        "date",
        "bank_id",
        "account",
        "currency",
        "debit",
        "credit",
    ),
}


def money(value):
    try:
        n = Decimal(value)
        if (
            not n.is_finite()
            or abs(n) > Decimal("1000000000000")
            or n != n.quantize(Decimal(".01"))
        ):
            raise ValueError(
                "Amounts must be finite, at most 1 trillion, with <=2 decimals"
            )
        return int(n * 100)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Invalid decimal amount") from exc


def parse_csv(text, kind):
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if (
        not reader.fieldnames
        or set(reader.fieldnames) != set(SCHEMAS[kind])
        or len(reader.fieldnames) != len(SCHEMAS[kind])
    ):
        raise ValueError(f'{kind}: expected columns {", ".join(SCHEMAS[kind])}')
    rows, seen = [], set()
    for line, raw in enumerate(reader, 2):
        if len(rows) >= 10000:
            raise ValueError(f"{kind}: maximum 10000 rows")
        if None in raw or any(v is None for v in raw.values()):
            raise ValueError(f"{kind} line {line}: malformed row")
        row = {k: v.strip() for k, v in raw.items()}
        if any(len(v) > 500 for v in row.values()):
            raise ValueError(f"{kind} line {line}: field too long")
        if not row["id"] or row["id"] in seen:
            raise ValueError(f"{kind} line {line}: empty or duplicate id")
        seen.add(row["id"])
        try:
            date.fromisoformat(row["date"])
        except ValueError as exc:
            raise ValueError(f"{kind} line {line}: use ISO date YYYY-MM-DD") from exc
        if row["currency"] not in ("TRY", "EUR", "USD", "GBP"):
            raise ValueError(f"{kind} line {line}: unsupported currency")
        if kind == "journal":
            if not row["entry_id"] or not row["account"]:
                raise ValueError("Journal entry_id/account required")
            for key in ("debit", "credit"):
                row[key] = money(row[key])
            if min(row["debit"], row["credit"]) < 0 or (
                (row["debit"] > 0) == (row["credit"] > 0)
            ):
                raise ValueError(
                    "Journal lines require exactly one positive debit or credit"
                )
        else:
            row["amount"] = money(row["amount"])
            if not row["party"] or row["amount"] == 0:
                raise ValueError("Party and nonzero amount required")
        rows.append(row)
    return rows


def reconcile(bank_csv, invoices_csv, journal_csv, days=45, tolerance=1):
    if (
        type(days) is not int
        or not 0 <= days <= 365
        or type(tolerance) is not int
        or not 0 <= tolerance <= 100
    ):
        raise ValueError("days must be 0..365; tolerance 0..100 minor units")
    inputs = dict(zip(SCHEMAS, (bank_csv, invoices_csv, journal_csv)))
    data = {k: parse_csv(v, k) for k, v in inputs.items()}
    banks, invoices, journal = (data[k] for k in SCHEMAS)
    inv = {r["id"]: r for r in invoices}
    issues, groups = [], []

    def issue(code, source, ids, detail):
        issues.append(dict(code=code, source=source, ids=sorted(ids), detail=detail))

    # Quarantine all members of suspected duplicate pairs, never pick one silently.
    duplicate = set()
    for kind in ("bank", "invoices", "journal"):
        buckets = defaultdict(list)
        for r in data[kind]:
            fields = (
                ("date", "party", "currency", "amount", "reference", "description")
                if kind == "bank"
                else (
                    ("date", "party", "currency", "amount", "description")
                    if kind == "invoices"
                    else (
                        "entry_id",
                        "date",
                        "bank_id",
                        "account",
                        "currency",
                        "debit",
                        "credit",
                    )
                )
            )
            buckets[tuple(r[k] for k in fields)].append(r["id"])
        for ids in buckets.values():
            if len(ids) > 1:
                duplicate.update((kind, x) for x in ids)
                issue(
                    "DUPLICATE_SUSPECT",
                    kind,
                    ids,
                    "Same business fields; all members quarantined",
                )
    entries = defaultdict(list)
    for r in journal:
        entries[r["entry_id"]].append(r)
    bad_entries = set()
    for eid, lines in entries.items():
        balances = defaultdict(int)
        for r in lines:
            balances[r["currency"]] += r["debit"] - r["credit"]
        if any(("journal", r["id"]) in duplicate for r in lines):
            bad_entries.add(eid)
        if len({r["date"] for r in lines}) != 1:
            bad_entries.add(eid)
            issue(
                "ENTRY_DATE_CONFLICT",
                "journal",
                [r["id"] for r in lines],
                f"Entry {eid}: lines use different posting dates",
            )
        if any(balances.values()):
            bad_entries.add(eid)
            issue(
                "UNBALANCED_ENTRY",
                "journal",
                [r["id"] for r in lines],
                f"Entry {eid}: debit/credit differ",
            )
    bank_ids = {r["id"] for r in banks}
    for r in journal:
        if r["bank_id"] and r["bank_id"] not in bank_ids:
            issue("ORPHAN_BANK_LINK", "journal", [r["id"]], "Unknown bank_id")
    ledger_ok = {}
    for b in banks:
        lines = [
            r for r in journal if r["bank_id"] == b["id"] and r["account"] == "BANK"
        ]
        ok = (
            bool(lines)
            and all(
                r["currency"] == b["currency"]
                and r["entry_id"] not in bad_entries
                and ("journal", r["id"]) not in duplicate
                and abs(
                    (date.fromisoformat(r["date"]) - date.fromisoformat(b["date"])).days
                )
                <= days
                for r in lines
            )
            and sum(r["debit"] - r["credit"] for r in lines) == b["amount"]
        )
        ledger_ok[b["id"]] = ok
        if not ok:
            issue(
                "LEDGER_MISMATCH",
                "bank",
                [b["id"]],
                "BANK lines missing, unbalanced, duplicated, stale, wrong currency or unequal amount",
            )
    # Explicit semicolon-separated invoice IDs form connected settlement components.
    links = {}
    for b in banks:
        refs = sorted(set(x.strip() for x in b["reference"].split(";") if x.strip()))
        if refs:
            links[b["id"]] = refs
    remaining = set(links)
    used_b, used_i = set(), set()
    bmap = {b["id"]: b for b in banks}

    def emit(bs, ids, rule, score, extra=None):
        ins = [inv[i] for i in ids if i in inv]
        flags = list(extra or [])
        currencies = {r["currency"] for r in bs + ins}
        if len(currencies) != 1:
            flags.append("CURRENCY_CONFLICT")
        if len({r["party"] for r in bs + ins}) != 1:
            flags.append("PARTY_CONFLICT")
        if any(i not in inv for i in ids):
            flags.append("UNKNOWN_REFERENCE")
        if any(
            (kind, r["id"]) in duplicate
            for kind, rows in (("bank", bs), ("invoices", ins))
            for r in rows
        ):
            flags.append("DUPLICATE_SUSPECT")
        if any(not ledger_ok[b["id"]] for b in bs):
            flags.append("LEDGER_MISMATCH")
        if any(
            abs((date.fromisoformat(b["date"]) - date.fromisoformat(i["date"])).days)
            > days
            for b in bs
            for i in ins
        ):
            flags.append("DATE_WINDOW")
        gross, cash = sum(i["amount"] for i in ins), sum(b["amount"] for b in bs)
        delta = cash - gross if len(currencies) == 1 else None
        if delta is not None and abs(delta) > tolerance:
            flags.append("AMOUNT_DIFFERENCE")
        # Fees are a hypothesis requiring review. Only use evidence from a valid
        # entry that also contains the linked BANK line; detached or unbalanced
        # fee rows must not explain a settlement difference.
        bank_entry_links = {
            (r["entry_id"], r["bank_id"])
            for r in journal
            if r["account"] == "BANK"
            and r["bank_id"] in {b["id"] for b in bs}
            and r["entry_id"] not in bad_entries
            and ("journal", r["id"]) not in duplicate
        }
        fee = sum(
            r["debit"] - r["credit"]
            for r in journal
            if r["account"] == "FEE"
            and r["bank_id"] in {b["id"] for b in bs}
            and len(currencies) == 1
            and r["currency"] in currencies
            and r["entry_id"] not in bad_entries
            and ("journal", r["id"]) not in duplicate
            and (r["entry_id"], r["bank_id"]) in bank_entry_links
            and ledger_ok[r["bank_id"]]
        )
        if delta is not None and delta < 0 and fee == -delta:
            flags.append("FEE_EXPLAINS_DIFFERENCE")
        if any((b["amount"] > 0) != (i["amount"] > 0) for b in bs for i in ins):
            flags.append("DIRECTION_CONFLICT")
        status = "MATCHED" if not flags and rule == "REFERENCE" else "REVIEW"
        groups.append(
            dict(
                id=f"R{len(groups)+1:04}",
                bank_ids=[b["id"] for b in bs],
                invoice_ids=ids,
                rule=rule,
                score=score,
                status=status,
                currency=next(iter(currencies)) if len(currencies) == 1 else "MIXED",
                bank_amount=cash if len(currencies) == 1 else None,
                invoice_amount=gross if len(currencies) == 1 else None,
                difference=delta,
                flags=sorted(set(flags)),
                party=bs[0]["party"],
                shape=f"{len(bs)}:{len(ids)}",
            )
        )
        used_b.update(b["id"] for b in bs)
        used_i.update(ids)

    while remaining:
        component_b = {min(remaining)}
        component_i = set()
        changed = True
        while changed:
            previous = (len(component_b), len(component_i))
            for bid in sorted(component_b):
                component_i.update(links[bid])
            component_b.update(
                bid for bid in remaining if set(links[bid]) & component_i
            )
            changed = previous != (len(component_b), len(component_i))
        remaining -= component_b
        emit(
            [bmap[i] for i in sorted(component_b)],
            sorted(component_i),
            "REFERENCE",
            100,
        )
    # Non-reference suggestions require unique candidates on BOTH sides.
    candidates = {}
    for b in banks:
        if b["id"] in used_b or ("bank", b["id"]) in duplicate:
            continue
        eligible = []
        for i in invoices:
            if i["id"] in used_i or ("invoices", i["id"]) in duplicate:
                continue
            if (
                b["currency"] == i["currency"]
                and b["party"] == i["party"]
                and abs(b["amount"] - i["amount"]) <= tolerance
                and abs(
                    (date.fromisoformat(b["date"]) - date.fromisoformat(i["date"])).days
                )
                <= days
            ):
                eligible.append(i["id"])
        candidates[b["id"]] = eligible
    frequency = Counter(i for ids in candidates.values() for i in ids)
    for bid, ids in sorted(candidates.items()):
        if len(ids) == 1 and frequency[ids[0]] == 1:
            b, i = bmap[bid], inv[ids[0]]
            similarity = SequenceMatcher(
                None, b["description"].casefold(), i["description"].casefold()
            ).ratio()
            emit(
                [b],
                ids,
                "AMOUNT_DATE_PARTY",
                round(70 + 20 * similarity),
                ["REFERENCE_MISSING"],
            )
        elif ids:
            issue(
                "AMBIGUOUS_MATCH",
                "bank",
                [bid],
                f"{len(ids)} candidate invoice(s); no allocation made",
            )
    for b in banks:
        if b["id"] not in used_b:
            issue(
                "UNALLOCATED_BANK", "bank", [b["id"]], "No unique supported settlement"
            )
    for i in invoices:
        if i["id"] not in used_i:
            issue(
                "OPEN_INVOICE",
                "invoices",
                [i["id"]],
                "No allocated settlement in this input window",
            )
    totals = {}
    for currency in sorted({r["currency"] for r in banks + invoices}):
        matched_ids = {
            bid for g in groups if g["status"] == "MATCHED" for bid in g["bank_ids"]
        }
        totals[currency] = dict(
            bank_net=sum(b["amount"] for b in banks if b["currency"] == currency),
            invoice_net=sum(i["amount"] for i in invoices if i["currency"] == currency),
            matched_gross=sum(
                abs(b["amount"])
                for b in banks
                if b["currency"] == currency and b["id"] in matched_ids
            ),
            unresolved_gross=sum(
                abs(b["amount"])
                for b in banks
                if b["currency"] == currency and b["id"] not in matched_ids
            ),
        )
    manifest = dict(
        version=VERSION,
        input_sha256={
            k: hashlib.sha256(v.encode()).hexdigest() for k, v in inputs.items()
        },
        policy=dict(days=days, tolerance_minor_units=tolerance),
    )
    run_id = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[
        :16
    ]
    return dict(
        run_id=run_id,
        manifest=manifest,
        counts={k: len(v) for k, v in data.items()},
        groups=groups,
        issues=issues,
        totals=totals,
        summary=dict(
            matched=sum(g["status"] == "MATCHED" for g in groups),
            review=sum(g["status"] == "REVIEW" for g in groups),
            issues=len(issues),
        ),
    )


def export_csv(result):
    out = io.StringIO()
    fields = (
        "id",
        "status",
        "party",
        "currency",
        "bank_amount",
        "invoice_amount",
        "difference",
        "rule",
        "score",
        "shape",
        "bank_ids",
        "invoice_ids",
        "flags",
    )
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for group in result["groups"]:
        row = {
            k: ";".join(group[k]) if isinstance(group[k], list) else group[k]
            for k in fields
        }
        for k, v in row.items():
            if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")):
                row[k] = "'" + v
        writer.writerow(row)
    return out.getvalue()
