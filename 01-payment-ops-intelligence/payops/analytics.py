"""Deterministic analytics for the Trend and Summary agents (pandas - never the LLM - computes numbers)."""

from functools import lru_cache

import pandas as pd

from payops.config import get_settings
from payops.loaders import load_incidents

SEVERITY_ORDER = ["Sev1", "Sev2", "Sev3", "Sev4"]


@lru_cache
def incidents_df() -> pd.DataFrame:
    return pd.DataFrame(load_incidents(get_settings().data_dir / "incidents.csv"))


def filter_df(df: pd.DataFrame, category: str | None = None, system: str | None = None,
              payment_type: str | None = None, months: list[str] | None = None) -> pd.DataFrame:
    if category:
        df = df[df.failure_category == category]
    if system:
        df = df[df.system == system]
    if payment_type:
        df = df[df.payment_type == payment_type]
    if months:
        df = df[df.month.isin(months)]
    return df


def trend_report(category: str | None = None, system: str | None = None, payment_type: str | None = None,
                 months: list[str] | None = None) -> dict:
    df = filter_df(incidents_df(), category, system, payment_type, months)
    if df.empty:
        return {"incidents": 0}
    all_months = sorted(incidents_df().month.unique())
    monthly = df.groupby("month").size().reindex(all_months if not months else sorted(months), fill_value=0)
    last2, prior = monthly.iloc[-2:].mean(), monthly.iloc[:-2].mean() if len(monthly) > 2 else 0.0
    direction = "rising" if last2 > prior * 1.25 else "falling" if last2 < prior * 0.75 else "stable"
    by_cat = df.groupby("failure_category").agg(incidents=("incident_id", "count"),
                                                  mttr_hours=("resolution_time_hours", "mean"),
                                                  amount_usd=("amount_usd", "sum"))
    recent_by_cat = df[df.month.isin(all_months[-2:])].groupby("failure_category").size()
    earlier_by_cat = df[~df.month.isin(all_months[-2:])].groupby("failure_category").size()
    month_end = int((pd.to_datetime(df.date).dt.day >= 28).sum())
    return {
        "filters": {k: v for k, v in {"category": category, "system": system, "payment_type": payment_type,
                                       "months": months}.items() if v},
        "incidents": len(df),
        "monthly_counts": {m: int(c) for m, c in monthly.items()},
        "direction": direction,
        "avg_last_2_months": round(float(last2), 1),
        "avg_prior_months": round(float(prior), 1),
        "by_severity": {s: int((df.severity == s).sum()) for s in SEVERITY_ORDER},
        "by_category": {c: {"incidents": int(r.incidents), "mttr_hours": round(float(r.mttr_hours), 1),
                            "amount_usd": round(float(r.amount_usd), 2)} for c, r in by_cat.iterrows()},
        "by_system": {s: int(c) for s, c in df.groupby("system").size().items()},
        "rising_categories": sorted(c for c in recent_by_cat.index
                                    if recent_by_cat[c] / 2 > earlier_by_cat.get(c, 0) / max(len(all_months) - 2, 1) * 1.5),
        "month_end_share_pct": round(100 * month_end / len(df), 1),
        "total_amount_usd": round(float(df.amount_usd.sum()), 2),
        "mttr_hours": round(float(df.resolution_time_hours.mean()), 1),
    }


def recent_high_severity(limit: int = 5) -> list[dict]:
    df = incidents_df()
    hs = df[df.severity.isin(["Sev1", "Sev2"])].sort_values("date", ascending=False).head(limit)
    return hs[["incident_id", "date", "severity", "failure_category", "title", "amount_usd"]].to_dict("records")


def render(report: dict) -> str:
    """Plain-text table the LLM narrates - numbers in the answer must come from here."""
    if not report.get("incidents"):
        return "No incidents match the filters."
    lines = [(f"Incidents: {report['incidents']} | trend: {report['direction']} "
              f"(avg {report['avg_last_2_months']}/month in the last 2 months vs {report['avg_prior_months']} before)"),
             f"Total amount affected: ${report['total_amount_usd']:,.2f} | mean time to resolve: {report['mttr_hours']} h",
             f"Share of incidents on month-end days (28-31): {report['month_end_share_pct']}%",
             "Monthly counts: " + ", ".join(f"{m}: {c}" for m, c in report["monthly_counts"].items()),
             "By severity: " + ", ".join(f"{s}: {c}" for s, c in report["by_severity"].items()),
             "By system: " + ", ".join(f"{s}: {c}" for s, c in report["by_system"].items()),
             "By category (incidents / MTTR h / amount $):"]
    lines += [f"  {c}: {v['incidents']} / {v['mttr_hours']} / {v['amount_usd']:,.2f}" for c, v in report["by_category"].items()]
    if report["rising_categories"]:
        lines.append("Rising in the last 2 months: " + ", ".join(report["rising_categories"]))
    return "\n".join(lines)
