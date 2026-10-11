---
doc_id: QCS-002
title: Statistical Process Control (SPC) and Process Capability
revision: C
owner: Quality Engineer
effective: 2026-01-10
---

# Statistical Process Control (SPC) and Process Capability

## Control Charts
CTQ dimensions are monitored on X-bar and R charts with a subgroup size of 5, taken every 2 hours. Control limits are calculated from at least 25 subgroups after the process is stable and are recalculated only after an approved process change.

## Out-of-Control Rules (Western Electric)
React when any of the following occur:
1. One point beyond the 3-sigma control limits.
2. Two of three consecutive points beyond 2 sigma on the same side.
3. Four of five consecutive points beyond 1 sigma on the same side.
4. Eight consecutive points on the same side of the center line.
5. Six consecutive points steadily increasing or decreasing (trend).

## Reaction Plan for an Out-of-Control Signal
1. Stop the process and notify the shift supervisor.
2. Quarantine all parts produced since the last in-control subgroup and tag them with a yellow HOLD tag.
3. Identify and correct the assignable cause (tool wear, offset, material, fixture).
4. Inspect the quarantined parts 100% for the affected characteristic.
5. Record the cause and action on the SPC chart and in the MES.
6. Restart only after the next subgroup is within control limits and Quality approves.

## Process Capability Requirements
- New processes must demonstrate Cpk of at least 1.67 before production approval (PPAP).
- Ongoing production must maintain Cpk of at least 1.33 on all CTQ characteristics.
- If Cpk falls between 1.00 and 1.33, increase inspection to 100% on that characteristic and open a corrective action (see QCS-003).
- If Cpk is below 1.00, stop production and escalate to the Quality Engineer (ext. 4420).

## Calculating Cpk
Cpk = min( (USL - mean) / (3 * sigma), (mean - LSL) / (3 * sigma) ), using the within-subgroup sigma estimated as R-bar / d2 (d2 = 2.326 for n = 5).
