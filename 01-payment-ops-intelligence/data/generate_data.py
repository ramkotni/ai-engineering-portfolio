"""Generates the synthetic sample data for Payment Operations Intelligence.

    python data/generate_data.py

Outputs (committed, so the project runs without this step):
  data/raw/incidents.csv            60 payment incidents, Apr-Sep 2026
  data/raw/business_rules.md        operational rules used by the Recommendation Agent
  data/raw/reports/*.html           weekly payment monitoring reports (HTML with tables)

All systems, vendors, IDs and amounts are fictional. Patterns are planted on purpose so the
Trend Agent has something real to find:
  - payment timeouts cluster at month-end (days 28-31)
  - duplicate payments rise after gateway release v4.2 (August)
  - SFTP certificate expiry hits in June only
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

RAW = Path(__file__).parent / "raw"
random.seed(42)

CATEGORIES = {
    "bank_file_rejection": {
        "system": "Bank File Transfer",
        "payment_types": ["ACH"],
        "titles": ["ACH file rejected by bank", "NACHA file failed bank validation", "Outbound ACH batch returned"],
        "symptoms": [
            "Bank returned the outbound NACHA file with error R-BATCH: batch control total does not match entry detail count.",
            "Morning ACH file rejected at bank gateway; file header record count mismatch reported.",
        ],
        "root_causes": [
            "Settlement engine patch changed batch grouping so the batch control count no longer matched the entry count.",
            "A manual re-run appended entries to an already-closed batch, breaking the batch control totals.",
        ],
        "resolutions": [
            "Regenerated the ACH file with corrected batch control records and added a pre-transmission NACHA validation step.",
            "Rebuilt the batch from the settlement ledger and blocked manual re-runs on closed batches.",
        ],
    },
    "duplicate_payment": {
        "system": "Payment Gateway",
        "payment_types": ["Wire", "ACH"],
        "titles": ["Duplicate wire sent to vendor", "Vendor paid twice", "Duplicate payment detected in reconciliation"],
        "symptoms": [
            "Reconciliation flagged two identical wires to the same vendor within 4 minutes.",
            "Vendor reported receiving the same invoice amount twice on the same day.",
        ],
        "root_causes": [
            "Gateway retry logic resubmitted the payment after a timeout without an idempotency key (introduced in gateway release v4.2).",
            "Operator re-released a payment that had already been sent because the status page showed it as pending.",
        ],
        "resolutions": [
            "Enabled idempotency keys on gateway retries, recalled the duplicate through treasury and reconciled the vendor ledger.",
            "Recalled the duplicate, fixed the status refresh and added a duplicate check on vendor + amount + date before release.",
        ],
    },
    "payment_timeout": {
        "system": "Payment Gateway",
        "payment_types": ["Wire", "ACH"],
        "titles": ["Bank API timeout during payment run", "Payment run stalled on bank API", "Wire submission timeouts"],
        "symptoms": [
            "Bank API calls exceeded the 30 second timeout during the month-end payment run; 140 payments queued.",
            "Wire submissions timed out repeatedly between 16:00 and 17:00.",
        ],
        "root_causes": [
            "Month-end volume peak pushed bank API latency above the 30 second gateway timeout.",
            "Bank throttled requests because the payment run submitted in one burst instead of in batches.",
        ],
        "resolutions": [
            "Raised the gateway timeout to 60 seconds and moved the bulk run to a 06:00 window outside the peak.",
            "Batched submissions in groups of 50 with back-off and agreed a month-end capacity window with the bank.",
        ],
    },
    "invalid_routing_number": {
        "system": "Vendor Master",
        "payment_types": ["ACH", "Wire"],
        "titles": ["Payment returned - invalid routing number", "ACH return R03 for vendor", "Wire rejected for bad ABA number"],
        "symptoms": [
            "ACH entries returned with R03 (no account / unable to locate) for a recently updated vendor.",
            "Wire rejected by the intermediary bank: invalid ABA routing number.",
        ],
        "root_causes": [
            "Vendor master bank details were updated with a mistyped ABA routing number during onboarding.",
            "Bulk vendor import skipped ABA checksum validation.",
        ],
        "resolutions": [
            "Corrected the vendor master record after call-back verification and added ABA checksum validation on edit.",
            "Re-validated all imported vendors and made checksum validation mandatory in the import job.",
        ],
    },
    "reconciliation_mismatch": {
        "system": "Invoice Matching",
        "payment_types": ["ACH", "Wire", "Check"],
        "titles": ["Settlement vs GL reconciliation break", "Daily reconciliation mismatch", "Cash application out of balance"],
        "symptoms": [
            "Daily reconciliation showed a variance between settlement totals and the general ledger.",
            "Invoice matching and settlement disagreed by cents on a large number of invoices.",
        ],
        "root_causes": [
            "Invoice matching rounded line amounts half-up while the GL used banker's rounding.",
            "Currency conversion rate snapshot differed between invoice matching and settlement.",
        ],
        "resolutions": [
            "Aligned rounding to banker's rounding at 2 decimals in both systems and posted a correcting journal.",
            "Pinned a single daily FX snapshot shared by invoice matching and settlement.",
        ],
    },
    "credential_expiry": {
        "system": "Bank File Transfer",
        "payment_types": ["ACH", "Wire"],
        "titles": ["SFTP certificate expired", "Bank connection authentication failure", "File transfer to bank failed - auth"],
        "symptoms": [
            "Outbound SFTP connection to the bank failed with a certificate validation error; no files transmitted.",
        ],
        "root_causes": [
            "The SFTP client certificate used for bank file transfer expired; no expiry alert was configured.",
        ],
        "resolutions": [
            "Renewed the certificate with the bank, re-sent the queued files and added a 30-day certificate expiry alert.",
        ],
    },
    "settlement_delay": {
        "system": "Settlement Engine",
        "payment_types": ["ACH", "Wire", "Check"],
        "titles": ["Settlement window missed", "Late settlement of market payments", "Settlement batch delayed"],
        "symptoms": [
            "Settlement batch completed after the 14:00 bank cut-off; payments moved to next business day.",
            "Settlement job waited on invoice approvals and missed the daily window.",
        ],
        "root_causes": [
            "Invoice approval backlog upstream delayed the settlement job past the bank cut-off.",
            "Settlement job dependency on a nightly data load that ran 3 hours late.",
        ],
        "resolutions": [
            "Escalated pending approvals, ran an off-cycle settlement and added a cut-off monitor at 12:30.",
            "Decoupled settlement from the nightly load and added a data-freshness check with alerting.",
        ],
    },
}
SEVERITY_WEIGHTS = {"Sev1": 1, "Sev2": 3, "Sev3": 5, "Sev4": 3}
MONTHS = [(2026, m) for m in range(4, 10)]  # Apr - Sep 2026
DETECTED_BY = ["monitoring alert", "reconciliation job", "vendor report", "bank notification", "operator"]


def month_weight(category: str, year: int, month: int) -> int:
    """Planted trends."""
    if category == "duplicate_payment":
        return 4 if month >= 8 else 1          # gateway v4.2 released in August
    if category == "credential_expiry":
        return 3 if month == 6 else 0          # certificate expiry in June only
    if category == "payment_timeout":
        return 2
    return 1


def incident_day(category: str, year: int, month: int) -> date:
    last = (date(year, month % 12 + 1, 1) if month < 12 else date(year + 1, 1, 1)) - timedelta(days=1)
    if category == "payment_timeout":
        return date(year, month, random.randint(28, last.day))   # month-end peak
    return date(year, month, random.randint(1, last.day))


def generate_incidents(n: int = 60) -> list[dict]:
    pool = [(c, y, m) for c in CATEGORIES for (y, m) in MONTHS for _ in range(month_weight(c, y, m))]
    rows = []
    for i, (cat, y, m) in enumerate(sorted(random.choices(pool, k=n), key=lambda t: (t[1], t[2]))):
        spec = CATEGORIES[cat]
        sev = random.choices(list(SEVERITY_WEIGHTS), weights=SEVERITY_WEIGHTS.values())[0]
        if cat in ("duplicate_payment", "credential_expiry") and sev == "Sev4":
            sev = "Sev2"
        k = random.randrange(len(spec["root_causes"]))
        amount = round(random.uniform(8_000, 450_000), 2) if cat != "credential_expiry" else round(random.uniform(200_000, 2_500_000), 2)
        hours = {"Sev1": random.uniform(2, 8), "Sev2": random.uniform(4, 24), "Sev3": random.uniform(8, 48), "Sev4": random.uniform(24, 96)}[sev]
        d = incident_day(cat, y, m)
        rows.append({
            "incident_id": f"PAY-INC-{1001 + i}",
            "date": d.isoformat(),
            "month": d.strftime("%Y-%m"),
            "system": spec["system"],
            "payment_type": random.choice(spec["payment_types"]),
            "failure_category": cat,
            "severity": sev,
            "title": random.choice(spec["titles"]),
            "description": random.choice(spec["symptoms"]),
            "root_cause": spec["root_causes"][k],
            "resolution": spec["resolutions"][min(k, len(spec["resolutions"]) - 1)],
            "amount_usd": f"{amount:.2f}",
            "payments_affected": random.randint(1, 180) if cat in ("payment_timeout", "bank_file_rejection", "settlement_delay") else random.randint(1, 6),
            "resolution_time_hours": f"{hours:.1f}",
            "detected_by": random.choice(DETECTED_BY),
            "vendor_account": f"****{random.randint(1000, 9999)}",
            "status": "resolved" if d < date(2026, 9, 25) else random.choice(["resolved", "monitoring"]),
        })
    return rows


BUSINESS_RULES = """# Payment Operations - Business Rules and Runbook

Document ID: PAY-RULES-001 | Owner: Payment Operations Manager | Revision: 3

## Severity and Response
- **Sev1** (payments to many vendors blocked, or more than $1,000,000 at risk): open an incident bridge within 15 minutes, page the on-call payment engineer and notify the Treasury Manager.
- **Sev2** (a payment run degraded or a single high-value payment at risk): acknowledge within 30 minutes and update stakeholders every 2 hours.
- **Sev3 / Sev4**: handle in business hours; resolve within 3 business days.

## Duplicate Payments
- Any duplicate payment above $50,000 requires a treasury recall request within 24 hours and notification to the Controller.
- Never re-release a payment whose status is pending without checking the bank confirmation first.
- Gateway retries must carry an idempotency key.

## Bank Files and Re-sends
- Do not re-send a bank file until reconciliation confirms which entries the bank accepted.
- Every regenerated NACHA file must pass the pre-transmission validation (batch counts, hash totals, ABA checksums).

## Vendor Bank Details
- Changes to vendor bank details require dual approval and call-back verification to a known phone number.
- Routing numbers must pass ABA checksum validation before they are saved.

## Cut-offs and Settlement
- The bank ACH cut-off is 14:00 Central; settlement must complete by 13:30.
- If settlement is at risk at 12:30, escalate pending invoice approvals to the Accounts Payable lead.

## Certificates and Credentials
- Bank connection certificates must have an expiry alert at 30 and 7 days.

## Read-only Assistant Policy
- The AI assistant may analyse, explain and recommend. It must never release, approve, cancel or modify payments or vendor bank details.
"""


def write_reports(rows: list[dict]) -> None:
    """Weekly monitoring reports as HTML pages with headings, narrative and tables."""
    for (y, m) in [(2026, 6), (2026, 8), (2026, 9)]:
        month_rows = [r for r in rows if r["month"] == f"{y}-{m:02d}"]
        by_system: dict[str, list[dict]] = {}
        for r in month_rows:
            by_system.setdefault(r["system"], []).append(r)
        table = "\n".join(
            f"<tr><td>{s}</td><td>{len(v)}</td><td>{sum(1 for x in v if x['severity'] in ('Sev1', 'Sev2'))}</td>"
            f"<td>{sum(float(x['resolution_time_hours']) for x in v) / len(v):.1f}</td></tr>"
            for s, v in sorted(by_system.items())
        )
        notable = "\n".join(f"<li>{r['incident_id']} ({r['severity']}, {r['failure_category']}): {r['title']}.</li>"
                            for r in month_rows if r["severity"] in ("Sev1", "Sev2"))
        commentary = {
            6: "June was dominated by a bank connection outage when the SFTP client certificate expired; files were held for several hours. Certificate expiry alerting has since been added.",
            8: "Gateway release v4.2 went live on 4 August. Since the release, duplicate payments have increased; early analysis points to retries without idempotency keys.",
            9: "Duplicate payments remained elevated in September. Month-end payment timeouts recurred during the last three days of the month.",
        }[m]
        html = f"""<!doctype html>
<html><head><title>Payment Monitoring Report {y}-{m:02d}</title></head>
<body>
<h1>Payment Monitoring Report - {date(y, m, 1).strftime('%B %Y')}</h1>
<p>Document ID: PAY-MON-{y}{m:02d} | Owner: Payment Operations | Classification: Internal</p>
<h2>Executive Commentary</h2>
<p>{commentary}</p>
<h2>Incidents by System</h2>
<table>
<tr><th>System</th><th>Incidents</th><th>Sev1/Sev2</th><th>Avg resolution (h)</th></tr>
{table}
</table>
<h2>Notable Incidents</h2>
<ul>
{notable or '<li>No Sev1 or Sev2 incidents.</li>'}
</ul>
<h2>Actions for Next Month</h2>
<ul>
<li>Track duplicate payment rate daily until idempotency keys are verified in production.</li>
<li>Review month-end capacity with the bank before the next close.</li>
</ul>
</body></html>
"""
        (RAW / "reports" / f"payment_monitoring_{y}_{m:02d}.html").write_text(html, encoding="utf-8")


def main() -> None:
    (RAW / "reports").mkdir(parents=True, exist_ok=True)
    rows = generate_incidents()
    with open(RAW / "incidents.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (RAW / "business_rules.md").write_text(BUSINESS_RULES, encoding="utf-8")
    write_reports(rows)
    print(f"Wrote {len(rows)} incidents, business rules and 3 HTML reports to {RAW}")


if __name__ == "__main__":
    main()
