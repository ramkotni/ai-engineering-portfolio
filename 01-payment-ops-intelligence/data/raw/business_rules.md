# Payment Operations - Business Rules and Runbook

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
