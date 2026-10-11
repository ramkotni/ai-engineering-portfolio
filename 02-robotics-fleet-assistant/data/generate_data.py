"""Generates the synthetic sample data for the Robotics Fleet Assistant.

    python data/generate_data.py

Outputs (committed):
  data/raw/robots.csv                40 robots: model, zone, battery health, cycles, utilisation, queue, status
  data/raw/incidents.csv             90 robot incidents (Jul-Sep 2026) with error code, root cause, resolution
  data/raw/maintenance_logs.csv      maintenance actions per robot
  data/raw/battery_telemetry.csv     30 days of daily battery health per robot
  data/raw/troubleshooting_guide.md  error-code guide with tables and procedures

Fictional fleet. Planted patterns for the agents to find:
  - R-1007, R-1015, R-1023 lose battery health ~0.6%/day (others ~0.05%/day)
  - Wi-Fi drops cluster in zone Z3-Pick near access point AP-07
  - navigation exceptions jump on robots running firmware 4.8.0
  - Z3-Pick is overloaded while two healthy Z3 robots sit under-used
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

RAW = Path(__file__).parent / "raw"
random.seed(7)

ZONES = ["Z1-Inbound", "Z2-Storage", "Z3-Pick", "Z4-Pack"]
MODELS = ["Drive-A", "Drive-B", "Lift-C"]
FAST_DEGRADING = {"R-1007", "R-1015", "R-1023"}
TODAY = date(2026, 9, 30)

EVENT_TYPES = {
    "battery_degradation": {
        "codes": ["BAT-101", "BAT-104"],
        "descriptions": ["Battery voltage sagged under load; robot returned to charger mid-task.",
                         "State of charge dropped 18% in 20 minutes during heavy lift."],
        "root_causes": ["Battery pack at end of life: high cycle count and reduced capacity.",
                        "Cell imbalance in battery pack after deep discharges."],
        "resolutions": ["Replaced battery pack (part BP-48V-20Ah) and recalibrated the charge controller.",
                        "Ran cell balancing cycle; scheduled pack replacement at next maintenance window."],
    },
    "sensor_fault": {
        "codes": ["SEN-210", "SEN-215"],
        "descriptions": ["Lidar reported obstruction with no object present; robot stopped repeatedly.",
                         "Bumper sensor stuck active; robot entered protective stop."],
        "root_causes": ["Dust build-up on the lidar window from the inbound dock area.",
                        "Damaged bumper sensor cable after minor collision with a pallet."],
        "resolutions": ["Cleaned the lidar window and added zone Z1 to the weekly sensor-cleaning route.",
                        "Replaced bumper sensor cable harness (part HAR-BMP-02)."],
    },
    "motor_fault": {
        "codes": ["MOT-310", "MOT-318"],
        "descriptions": ["Left drive motor over-current alarm while climbing the dock ramp.",
                         "Wheel motor encoder errors caused jerky movement."],
        "root_causes": ["Worn drive motor bearing increasing friction under load.",
                        "Encoder connector corrosion causing intermittent signal."],
        "resolutions": ["Replaced left drive motor (part DM-750W) and checked wheel alignment.",
                        "Cleaned and re-seated encoder connector; applied contact protectant."],
    },
    "barcode_scanner_error": {
        "codes": ["SCN-402", "SCN-405"],
        "descriptions": ["Floor fiducial barcode not read; robot lost localisation at a pick face.",
                         "Tote barcode read failures above 5% during pick waves."],
        "root_causes": ["Scanner lens misaligned after impact; read angle out of tolerance.",
                        "Worn floor fiducial labels in a high-traffic aisle."],
        "resolutions": ["Recalibrated the scanner mount and verified read rate above 99.5%.",
                        "Replaced worn floor fiducials in the aisle and added them to the quarterly inspection."],
    },
    "wifi_drop": {
        "codes": ["NET-501", "NET-503"],
        "descriptions": ["Robot lost Wi-Fi for 40 seconds and paused all tasks.",
                         "Repeated roaming failures between access points; heartbeat timeouts."],
        "root_causes": ["Weak coverage near access point AP-07 in zone Z3-Pick after racking was extended.",
                        "Access point AP-07 firmware bug causing roaming failures."],
        "resolutions": ["Added an access point near rack row 14 and adjusted AP-07 transmit power.",
                        "Upgraded AP-07 firmware and enabled fast roaming (802.11r)."],
    },
    "navigation_exception": {
        "codes": ["NAV-601", "NAV-607"],
        "descriptions": ["Path planner failed to find a route; robot stuck at an intersection.",
                         "Robot deviated from the planned path and triggered a localisation reset."],
        "root_causes": ["Path planner regression in firmware 4.8.0 with dynamic obstacle maps.",
                        "Map not updated after a racking change; stale no-go zones."],
        "resolutions": ["Rolled back to firmware 4.7.3 pending a vendor fix; reported regression.",
                        "Re-published the zone map after the racking change and cleared stale no-go zones."],
    },
}
SEVERITY = {"battery_degradation": "Medium", "sensor_fault": "Medium", "motor_fault": "High",
            "barcode_scanner_error": "Low", "wifi_drop": "Medium", "navigation_exception": "High"}


def robots() -> list[dict]:
    out = []
    for i in range(40):
        rid = f"R-{1001 + i}"
        zone = ZONES[i % 4]
        fw = "4.8.0" if i % 3 == 0 else "4.7.3"
        cycles = random.randint(300, 1400) + (900 if rid in FAST_DEGRADING else 0)
        health = round(random.uniform(82, 97) - (14 if rid in FAST_DEGRADING else 0), 1)
        util = round(random.uniform(55, 80), 1)
        queue = random.randint(2, 6)
        if zone == "Z3-Pick":
            util, queue = round(random.uniform(86, 97), 1), random.randint(9, 14)
        if rid in ("R-1031", "R-1035"):     # under-used healthy robots in Z3 (task optimisation target)
            util, queue, health = 34.0 + (i % 5), 1, 93.5
        status = "maintenance" if rid == "R-1015" else "error" if rid == "R-1019" else "active"
        out.append({"robot_id": rid, "model": MODELS[i % 3], "zone": zone, "firmware": fw,
                    "battery_health_pct": health, "charge_cycles": cycles,
                    "days_since_maintenance": random.randint(5, 120), "utilization_pct": util,
                    "tasks_queued": queue, "status": status})
    return out


def incidents(fleet: list[dict]) -> list[dict]:
    rows = []
    by_id = {r["robot_id"]: r for r in fleet}
    for n in range(90):
        r = random.choice(fleet)
        weights = {"battery_degradation": 3 if r["robot_id"] in FAST_DEGRADING else 1,
                   "sensor_fault": 1.2, "motor_fault": 0.8, "barcode_scanner_error": 1.2,
                   "wifi_drop": 4 if r["zone"] == "Z3-Pick" else 0.4,
                   "navigation_exception": 3 if r["firmware"] == "4.8.0" else 0.5}
        et = random.choices(list(weights), weights=weights.values())[0]
        spec = EVENT_TYPES[et]
        k = 1 if et == "navigation_exception" and r["firmware"] != "4.8.0" else 0 if et == "navigation_exception" else random.randrange(2)
        if et == "wifi_drop" and r["zone"] != "Z3-Pick":
            k = 1
        d = TODAY - timedelta(days=random.randint(0, 91))
        rows.append({
            "event_id": f"RB-EVT-{2001 + n}", "date": d.isoformat(), "robot_id": r["robot_id"], "zone": r["zone"],
            "model": r["model"], "firmware": r["firmware"], "event_type": et, "error_code": spec["codes"][k],
            "severity": SEVERITY[et], "description": spec["descriptions"][k], "root_cause": spec["root_causes"][k],
            "resolution": spec["resolutions"][k], "downtime_min": random.randint(10, 240),
        })
    rows.sort(key=lambda x: x["date"])
    for i, row in enumerate(rows):
        row["event_id"] = f"RB-EVT-{2001 + i}"
    assert all(row["robot_id"] in by_id for row in rows)
    return rows


def maintenance(fleet: list[dict]) -> list[dict]:
    actions = [("battery pack replacement", "BP-48V-20Ah"), ("lidar window cleaning", "-"), ("drive motor replacement", "DM-750W"),
               ("scanner recalibration", "-"), ("firmware update", "-"), ("wheel alignment", "-")]
    rows = []
    for i in range(60):
        r = random.choice(fleet)
        a, part = random.choice(actions)
        rows.append({"log_id": f"MNT-{3001 + i}", "date": (TODAY - timedelta(days=random.randint(0, 180))).isoformat(),
                     "robot_id": r["robot_id"], "zone": r["zone"], "action": a, "part": part,
                     "notes": f"{a.capitalize()} completed on {r['robot_id']}; post-check passed."})
    return sorted(rows, key=lambda x: x["date"])


def telemetry(fleet: list[dict]) -> list[dict]:
    rows = []
    for r in fleet:
        slope = 0.6 if r["robot_id"] in FAST_DEGRADING else random.uniform(0.02, 0.08)
        start = r["battery_health_pct"] + slope * 29
        for day in range(30):
            d = TODAY - timedelta(days=29 - day)
            rows.append({"date": d.isoformat(), "robot_id": r["robot_id"],
                         "battery_health_pct": round(start - slope * day + random.uniform(-0.15, 0.15), 2)})
    return rows


GUIDE = """# Robotics Fleet Troubleshooting Guide

Document ID: RB-GUIDE-001 | Owner: Robotics Maintenance Lead | Revision: 5

## Safety Before Any Work
- Put the robot in maintenance mode from the fleet console and wait for a full stop before approaching.
- Never disable, bypass or override the emergency stop, bumper or lidar safety field.
- Robots must not be moved into restricted or human-only zones; use the fleet console to re-route.

## Error Code Reference
| Code | Category | Likely cause | First action |
|---|---|---|---|
| BAT-101 | Battery | Pack at end of life (cycles above 1,800 or health below 75%) | Schedule battery pack replacement |
| BAT-104 | Battery | Cell imbalance after deep discharge | Run cell balancing, check charger |
| SEN-210 | Sensor | Dirty lidar window | Clean lidar window, check for dust sources |
| SEN-215 | Sensor | Bumper sensor cable damage | Inspect and replace harness HAR-BMP-02 |
| MOT-310 | Motor | Worn drive motor bearing | Replace drive motor DM-750W |
| MOT-318 | Motor | Encoder connector corrosion | Clean and re-seat encoder connector |
| SCN-402 | Scanner | Lens misalignment | Recalibrate scanner mount |
| SCN-405 | Scanner | Worn floor fiducials | Replace fiducial labels |
| NET-501 | Network | Weak Wi-Fi coverage | Survey coverage, add or tune access points |
| NET-503 | Network | Access point roaming bug | Update AP firmware, enable 802.11r |
| NAV-601 | Navigation | Path planner regression | Check firmware version; roll back if 4.8.0 |
| NAV-607 | Navigation | Stale map after layout change | Re-publish zone map |

## Battery Health Policy
- Replace a battery pack when health is below 75% or charge cycles exceed 1,800.
- A health decline faster than 0.3% per day means the pack should be inspected within 7 days.
- Robots below 80% health should not be assigned heavy-lift tasks.

## Preventive Maintenance Intervals
- Lidar and scanner cleaning: weekly in Z1-Inbound (dust), monthly elsewhere.
- Drive motor and wheel inspection: every 90 days or 1,000 operating hours.
- Firmware: stay on the fleet-approved version; 4.8.0 is on hold pending the path-planner fix.

## Workload Balancing Rules
- Target utilisation is 60-85% per robot.
- Move tasks from robots above 85% utilisation or with more than 8 queued tasks to healthy robots in the same zone below 60%.
- Only reassign to robots that are active, above 80% battery health and not flagged for maintenance.
- Task reassignment is executed by the shift lead in the fleet console; the assistant only recommends.
"""


def write(name: str, rows: list[dict]) -> None:
    with open(RAW / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    fleet = robots()
    write("robots.csv", fleet)
    write("incidents.csv", incidents(fleet))
    write("maintenance_logs.csv", maintenance(fleet))
    write("battery_telemetry.csv", telemetry(fleet))
    (RAW / "troubleshooting_guide.md").write_text(GUIDE, encoding="utf-8")
    print(f"Wrote robots, incidents, maintenance logs, telemetry and guide to {RAW}")


if __name__ == "__main__":
    main()
