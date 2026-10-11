"""Deterministic fleet analytics - the LLM never computes these numbers, it only explains them.

fleet_status        status / utilisation per zone
battery_analysis    30-day battery-health slope per robot (least squares) + policy flags
maintenance_risk    risk score per robot from battery, cycles, maintenance age and recent incidents
rebalance           workload moves from overloaded to under-used healthy robots in the same zone
"""

import numpy as np
import pandas as pd

from fleetops.data import table

BATTERY_REPLACE_HEALTH = 75.0     # RB-GUIDE-001 Battery Health Policy
BATTERY_REPLACE_CYCLES = 1800
FAST_DECLINE_PER_DAY = 0.3
OVERLOAD_UTIL, OVERLOAD_QUEUE, UNDERUSED_UTIL, MIN_HEALTH_FOR_TASKS = 85.0, 8, 60.0, 80.0


def _scope(df: pd.DataFrame, zones: list[str] | None, robot_id: str | None = None) -> pd.DataFrame:
    if zones:
        df = df[df.zone.isin(zones)]
    if robot_id:
        df = df[df.robot_id == robot_id]
    return df


def fleet_status(zones: list[str] | None = None) -> dict:
    r = _scope(table("robots"), zones)
    by_zone = r.groupby("zone").agg(robots=("robot_id", "count"), avg_util=("utilization_pct", "mean"),
                                    tasks_queued=("tasks_queued", "sum"))
    return {
        "robots": len(r),
        "by_status": {k: int(v) for k, v in r.status.value_counts().items()},
        "by_zone": {z: {"robots": int(v.robots), "avg_utilization_pct": round(float(v.avg_util), 1),
                        "tasks_queued": int(v.tasks_queued)} for z, v in by_zone.iterrows()},
        "fleet_utilization_pct": round(float(r.utilization_pct.mean()), 1) if len(r) else 0.0,
        "not_active": r[r.status != "active"][["robot_id", "status", "zone"]].to_dict("records"),
    }


def battery_analysis(zones: list[str] | None = None, robot_id: str | None = None) -> dict:
    t = _scope(table("battery_telemetry").merge(table("robots")[["robot_id", "zone", "charge_cycles"]], on="robot_id"),
               zones, robot_id)
    rows = []
    for rid, g in t.groupby("robot_id"):
        days = np.arange(len(g))
        slope = float(np.polyfit(days, g.sort_values("date").battery_health_pct.values, 1)[0])
        health = float(g.sort_values("date").battery_health_pct.iloc[-1])
        cycles = int(g.charge_cycles.iloc[0])
        flags = []
        if health < BATTERY_REPLACE_HEALTH or cycles > BATTERY_REPLACE_CYCLES:
            flags.append("replace pack")
        if -slope > FAST_DECLINE_PER_DAY:
            flags.append("fast decline - inspect within 7 days")
        rows.append({"robot_id": rid, "health_pct": round(health, 1), "decline_per_day": round(-slope, 2),
                     "charge_cycles": cycles, "flags": flags})
    rows.sort(key=lambda x: x["decline_per_day"], reverse=True)
    return {"robots_analyzed": len(rows), "flagged": [x for x in rows if x["flags"]], "fastest_decline": rows[:5],
            "fleet_avg_decline_per_day": round(float(np.mean([x["decline_per_day"] for x in rows])), 2) if rows else 0.0}


def maintenance_risk(zones: list[str] | None = None, top: int = 5) -> dict:
    robots = _scope(table("robots"), zones)
    batt = {x["robot_id"]: x for x in battery_analysis(zones)["fastest_decline"] + battery_analysis(zones)["flagged"]}
    inc = table("incidents")
    recent = inc[pd.to_datetime(inc.date) >= pd.to_datetime(inc.date).max() - pd.Timedelta(days=30)]
    counts = recent.groupby("robot_id").size()
    scored = []
    for _, r in robots.iterrows():
        b = batt.get(r.robot_id, {"decline_per_day": 0.0})
        score = (max(0.0, 90 - r.battery_health_pct) * 2            # low health
                 + min(r.charge_cycles / BATTERY_REPLACE_CYCLES, 1.5) * 20
                 + min(r.days_since_maintenance / 90, 1.5) * 15        # overdue PM
                 + b["decline_per_day"] * 40                           # fast battery decline
                 + int(counts.get(r.robot_id, 0)) * 8)                 # recent incidents
        reasons = []
        if r.battery_health_pct < BATTERY_REPLACE_HEALTH or r.charge_cycles > BATTERY_REPLACE_CYCLES:
            reasons.append("battery at replacement threshold")
        if b["decline_per_day"] > FAST_DECLINE_PER_DAY:
            reasons.append(f"battery declining {b['decline_per_day']}%/day")
        if r.days_since_maintenance > 90:
            reasons.append(f"{r.days_since_maintenance} days since maintenance")
        if counts.get(r.robot_id, 0) >= 2:
            reasons.append(f"{int(counts[r.robot_id])} incidents in 30 days")
        scored.append({"robot_id": r.robot_id, "zone": r.zone, "risk_score": round(float(score), 1), "reasons": reasons})
    scored.sort(key=lambda x: x["risk_score"], reverse=True)
    return {"top_risk": scored[:top]}


def rebalance(zones: list[str] | None = None) -> dict:
    r = _scope(table("robots"), zones)
    moves = []
    for zone, g in r.groupby("zone"):
        over = g[(g.utilization_pct > OVERLOAD_UTIL) | (g.tasks_queued > OVERLOAD_QUEUE)].sort_values("tasks_queued", ascending=False)
        under = g[(g.utilization_pct < UNDERUSED_UTIL) & (g.status == "active") & (g.battery_health_pct >= MIN_HEALTH_FOR_TASKS)]
        capacity = {u.robot_id: max(0, OVERLOAD_QUEUE - 2 - int(u.tasks_queued)) for _, u in under.iterrows()}
        for _, o in over.iterrows():
            surplus = int(o.tasks_queued) - 6
            for uid in list(capacity):
                if surplus <= 0 or capacity[uid] <= 0:
                    continue
                n = min(surplus, capacity[uid], 3)
                moves.append({"zone": zone, "from": o.robot_id, "to": uid, "tasks": n})
                capacity[uid] -= n
                surplus -= n
    overloaded = r[(r.utilization_pct > OVERLOAD_UTIL) | (r.tasks_queued > OVERLOAD_QUEUE)]
    return {"overloaded_robots": len(overloaded), "moves": moves, "tasks_moved": sum(m["tasks"] for m in moves)}


def render(name: str, data: dict) -> str:
    """Text the LLM narrates. Every number in an answer must come from here."""
    if name == "fleet_status":
        lines = [f"Robots: {data['robots']} | fleet utilisation {data['fleet_utilization_pct']}%",
                 "By status: " + ", ".join(f"{k}: {v}" for k, v in data["by_status"].items())]
        lines += [f"  {z}: {v['robots']} robots, avg utilisation {v['avg_utilization_pct']}%, {v['tasks_queued']} tasks queued"
                  for z, v in data["by_zone"].items()]
        lines += [f"  not active: {x['robot_id']} ({x['status']}, {x['zone']})" for x in data["not_active"]]
        return "\n".join(lines)
    if name == "battery":
        lines = [f"Robots analysed: {data['robots_analyzed']} | fleet average decline {data['fleet_avg_decline_per_day']}%/day"]
        lines += [f"  {x['robot_id']}: health {x['health_pct']}%, decline {x['decline_per_day']}%/day, {x['charge_cycles']} cycles"
                  f"{' - ' + '; '.join(x['flags']) if x['flags'] else ''}" for x in data["fastest_decline"]]
        lines += [f"  FLAG {x['robot_id']}: {'; '.join(x['flags'])}" for x in data["flagged"] if x not in data["fastest_decline"]]
        return "\n".join(lines)
    if name == "risk":
        return "\n".join(f"  {x['robot_id']} ({x['zone']}): risk {x['risk_score']} - {', '.join(x['reasons']) or 'composite score'}"
                         for x in data["top_risk"])
    if name == "rebalance":
        lines = [f"Overloaded robots: {data['overloaded_robots']} | proposed task moves: {data['tasks_moved']}"]
        lines += [f"  {m['zone']}: move {m['tasks']} tasks {m['from']} -> {m['to']}" for m in data["moves"]]
        return "\n".join(lines)
    raise ValueError(name)
