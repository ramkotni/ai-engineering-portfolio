"""CLI.

    python -m feasibility.cli train
    python -m feasibility.cli score data/raw/new_projects.csv
    python -m feasibility.cli advise PRJ-NEW-5
"""

import argparse
import json

import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser(prog="feasibility")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("train")
    s = sub.add_parser("score")
    s.add_argument("csv")
    a = sub.add_parser("advise")
    a.add_argument("project_id")
    args = p.parse_args()

    if args.cmd == "train":
        from feasibility.train import train

        card = train()
        print(json.dumps({k: card[k] for k in ("model", "selection_reason", "test_metrics")}, indent=2))
    elif args.cmd == "score":
        from feasibility.predict import predict_batch

        for r in predict_batch(pd.read_csv(args.csv)):
            print(f"{r['project_id']:12s} {r['feasibility_probability']:.3f} {r['risk_band']:12s} "
                  f"risks: {', '.join(d['feature'] for d in r['top_negative_drivers'])}")
    else:
        from feasibility.advisor import build_advisor
        from feasibility.config import get_settings

        rows = pd.read_csv(get_settings().data_dir / "new_projects.csv")
        row = rows[rows.project_id == args.project_id].iloc[0].to_dict()
        st = build_advisor().invoke({"project": row, "notes": ""})
        print(st["advice"])
        print("\n" + " -> ".join(st["trace"]))


if __name__ == "__main__":
    main()
