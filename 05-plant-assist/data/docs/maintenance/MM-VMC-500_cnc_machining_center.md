---
doc_id: MM-VMC-500
title: VMC-500 Vertical Machining Center - Maintenance Manual
revision: 2
owner: Maintenance Planner
effective: 2026-02-15
---

# VMC-500 Vertical Machining Center - Maintenance Manual

## Machine Overview
The VMC-500 is a 3-axis vertical machining center with a 12,000 rpm spindle, a 24-station tool changer, and a flood coolant system with a 75-gallon sump. Apply lockout/tagout per SOP-SAF-001 before opening the electrical cabinet or reaching into the tool changer.

## Daily Checks (Operator)
- Verify way-lube reservoir level; refill with ISO VG 68 way oil.
- Check coolant concentration with the refractometer: target 6-8% (refractometer factor 1.0 for CoolCut 40). Adjust with premix from the central mixing station only.
- Blow chips from the tool changer with low-pressure air (max 30 psi), never at the spindle taper.
- Confirm air supply pressure is 85-100 psi at the regulator.

## Weekly Tasks
- Clean the chip conveyor and coolant tank screens.
- Wipe and inspect the spindle taper and tool holders for nicks and rust.
- Check the way covers for damage.

## Monthly and Periodic Tasks
- Monthly: clean the electrical cabinet air filter; check spindle drawbar clamping force with the gauge (minimum 4,500 lbf).
- Every 6 months: check ballscrew backlash (limit 0.0004 in / 0.010 mm) and update backlash compensation if needed.
- Annually: ballbar test for circular accuracy (limit 0.0008 in / 0.020 mm circularity) and spindle vibration analysis.

## Spindle Warm-Up Procedure
Run the spindle warm-up program O9000 at the start of each shift and after the machine has been idle for more than 4 hours: 10 minutes total, stepping 2,000 / 6,000 / 10,000 rpm. Skipping warm-up can cause thermal growth of up to 0.0015 in on the Z axis during the first hour.

## Common Alarms and Troubleshooting
- Alarm 1025 "Spindle overload": reduce feed or depth of cut, check tool wear, check for chip packing.
- Alarm 2041 "Low way-lube": refill the reservoir and check the lines for blockage.
- Alarm 3007 "Tool changer fault": apply LOTO, check the carousel for chips or a misaligned pocket, then home the tool changer.
- Poor surface finish: check tool runout (limit 0.0002 in TIR), coolant concentration, and spindle bearing condition.

## Escalation
Contact the Maintenance Planner (ext. 4410) for spindle rebuilds or any crash that results in axis misalignment.
