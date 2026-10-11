# Robotics Fleet Troubleshooting Guide

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
