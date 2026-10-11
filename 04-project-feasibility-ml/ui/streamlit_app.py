"""Project Feasibility - demo UI.   streamlit run ui/streamlit_app.py --server.port 8504"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from feasibility.config import get_settings
from feasibility.predict import ProjectInput, load_model, predict

st.set_page_config(page_title="Project Feasibility", layout="wide")
st.title("Project Feasibility Prediction")
model, card = load_model()
st.caption(f"Model: {card['model']} - test ROC-AUC {card['test_metrics']['roc_auc']} - {card['selection_reason']}")

tab_one, tab_batch, tab_model = st.tabs(["Score a project", "Score the pipeline", "Model card"])
with tab_one:
    c = st.columns(3)
    p = ProjectInput(
        project_type=c[0].selectbox("Type", ["application", "infrastructure", "data_platform", "ai_ml", "integration"]),
        region=c[0].selectbox("Region", ["americas", "emea", "apj"]),
        complexity=c[0].slider("Complexity", 1, 10, 6),
        budget_usd=c[1].number_input("Budget (USD)", 10_000, 20_000_000, 450_000, step=10_000),
        timeline_weeks=c[1].slider("Timeline (weeks)", 2, 104, 40),
        tech_readiness=c[1].slider("Technology readiness (TRL)", 1, 9, 5),
        resource_availability=c[2].slider("Resources secured", 0.0, 1.0, 0.6),
        dependency_count=c[2].slider("Dependencies", 0, 20, 4),
        team_experience_years=c[2].slider("Team experience (years)", 0.0, 20.0, 5.0),
        stakeholder_count=c[2].slider("Stakeholder groups", 1, 40, 8),
    )
    r = predict(p)
    m = st.columns(3)
    m[0].metric("Feasibility probability", f"{r['feasibility_probability']:.0%}")
    m[1].metric("Risk band", r["risk_band"])
    m[2].metric("Budget per week", f"${r['budget_per_week_usd']:,}")
    for w in r["ood_warnings"]:
        st.warning(f"Out of training range: {w}")
    drivers = pd.DataFrame(r["top_negative_drivers"] + r["top_positive_drivers"])
    if not drivers.empty:
        st.bar_chart(drivers.set_index("description")["contribution"])
    notes = st.text_area("Notes for the advisor (optional)")
    if st.button("Get advice (LLM)"):
        from feasibility.advisor import build_advisor

        with st.spinner("Advisor thinking..."):
            out = build_advisor().invoke({"project": p.model_dump(), "notes": notes})
        st.markdown(out["advice"])
        st.caption(" -> ".join(out["trace"]))
with tab_batch:
    new = pd.read_csv(get_settings().data_dir / "new_projects.csv")
    scored = pd.DataFrame([predict(ProjectInput(**{k: (v.item() if hasattr(v, "item") else v) for k, v in row.items()}))
                           for row in new.to_dict("records")])
    st.dataframe(scored[["project_id", "feasibility_probability", "risk_band", "model"]], use_container_width=True)
with tab_model:
    st.json({k: card[k] for k in ("model", "selection_reason", "comparison", "test_metrics", "intended_use", "limitations")})
    st.dataframe(pd.DataFrame(card["coefficients"]))
