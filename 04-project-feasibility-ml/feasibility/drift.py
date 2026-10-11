"""Input drift monitoring with the Population Stability Index (PSI) against the training distribution.

PSI < 0.1 stable | 0.1-0.25 moderate shift | > 0.25 significant shift -> investigate / retrain.
The API keeps a rolling window of recent prediction inputs; GET /drift reports PSI per feature.
"""

from collections import deque
from threading import Lock

import numpy as np

from feasibility.data import NUMERIC

WINDOW: deque = deque(maxlen=500)
_lock = Lock()


def record(row: dict) -> None:
    with _lock:
        WINDOW.append({c: row[c] for c in NUMERIC})


def psi(stats: dict, values: np.ndarray) -> float:
    """PSI between the training histogram (bins + expected shares saved at train time) and recent inputs."""
    edges, expected = np.array(stats["bins"]), np.array(stats["expected"])
    if len(edges) < 2 or len(values) == 0:
        return 0.0
    actual = np.histogram(np.clip(values, edges[0], edges[-1]), bins=edges)[0] / len(values)
    expected, actual = np.clip(expected, 1e-4, None), np.clip(actual, 1e-4, None)
    return float(np.sum((actual - expected) * np.log(actual / expected)))


def drift_report(card: dict, rows: list[dict] | None = None) -> dict:
    with _lock:
        rows = list(rows if rows is not None else WINDOW)
    out = {"window_size": len(rows), "features": {}}
    if len(rows) < 30:
        out["note"] = "need at least 30 predictions for a reliable PSI"
    for c in NUMERIC:
        vals = np.array([r[c] for r in rows if r.get(c) is not None], dtype=float)
        value = psi(card["training_stats"][c], vals[~np.isnan(vals)])
        out["features"][c] = {"psi": round(value, 3),
                              "status": "stable" if value < 0.1 else "moderate" if value < 0.25 else "significant"}
    return out
