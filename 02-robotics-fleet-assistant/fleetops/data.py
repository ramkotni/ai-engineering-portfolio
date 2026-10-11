"""Loading and rendering of the fleet data (CSV + Markdown guide)."""

from functools import lru_cache

import pandas as pd

from fleetops.config import get_settings


@lru_cache
def table(name: str) -> pd.DataFrame:
    return pd.read_csv(get_settings().data_dir / f"{name}.csv")


def incident_text(r) -> str:
    return (f"{r['event_id']} | {r['date']} | {r['robot_id']} | {r['zone']} | {r['model']} | firmware {r['firmware']} | "
            f"{r['event_type']} | {r['error_code']} | severity {r['severity']}\n"
            f"Symptom: {r['description']}\nRoot cause: {r['root_cause']}\nResolution: {r['resolution']}\n"
            f"Downtime: {r['downtime_min']} min")


def maintenance_text(r) -> str:
    return (f"{r['log_id']} | {r['date']} | {r['robot_id']} | {r['zone']} | maintenance: {r['action']} | part {r['part']}\n"
            f"Notes: {r['notes']}")


def robot_text(r) -> str:
    return (f"{r['robot_id']} ({r['model']}, zone {r['zone']}, firmware {r['firmware']}): status {r['status']}, "
            f"battery health {r['battery_health_pct']}%, {r['charge_cycles']} charge cycles, "
            f"{r['days_since_maintenance']} days since maintenance, utilisation {r['utilization_pct']}%, "
            f"{r['tasks_queued']} tasks queued")
