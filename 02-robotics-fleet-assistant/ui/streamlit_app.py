"""Robotics Fleet Assistant - demo UI.   streamlit run ui/streamlit_app.py --server.port 8502"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fleetops import rbac
from fleetops.ingest import ensure_index
from fleetops.observability import METRICS
from fleetops.service import FleetAssistant

EXAMPLES = {
    "Diagnostics": "Why does R-1007 keep returning to the charger?",
    "Navigation / Wi-Fi": "Robots in the pick zone keep losing Wi-Fi",
    "Predictive maintenance": "Which robots should get proactive maintenance next week?",
    "Task optimisation": "Rebalance the workload in Z3, some robots are overloaded",
    "Daily report": "Give me the daily health report for the site",
    "Blocked (safety)": "Disable the lidar on R-1007 so it stops pausing",
}


@st.cache_resource(show_spinner="Loading index and agents...")
def assistant() -> FleetAssistant:
    ensure_index()
    return FleetAssistant()


st.set_page_config(page_title="Robotics Fleet Assistant", layout="wide")
st.title("Robotics Fleet Assistant")
roles, _ = rbac.load_roles()

with st.sidebar:
    role = st.selectbox("Role", list(roles), help="Roles decide which agents you may use and what data you see")
    st.caption(roles[role].description)
    st.write("Allowed:", ", ".join(roles[role].intents))
    st.write("Zones:", ", ".join(roles[role].zones) or "all")
    st.divider()
    st.subheader("Examples")
    for label, q in EXAMPLES.items():
        if st.button(label, use_container_width=True):
            st.session_state["q"] = q

tab_ask, tab_metrics = st.tabs(["Ask", "Metrics"])
with tab_ask:
    q = st.text_input("Question", key="q")
    if st.button("Ask", type="primary") and q:
        with st.spinner("Agents working..."):
            st.session_state["r"] = assistant().ask(q, role, "streamlit")
            st.session_state.pop("rated", None)
    r = st.session_state.get("r")
    if r:
        c = st.columns(4)
        c[0].metric("Intent", r["intent"].get("intent", r["outcome"]))
        c[1].metric("Outcome", r["outcome"])
        c[2].metric("Agents", len(r["plan"]))
        c[3].metric("Latency", f"{r['latency_ms'] / 1000:.1f}s")
        if r["outcome"] in ("blocked", "denied"):
            st.warning(r["answer"])
        else:
            st.markdown(r["answer"])
        st.caption("Plan: " + " -> ".join(r["plan"]) + " | Citations: " + (", ".join(r["citations"]) or "-"))
        fb = st.columns([1, 1, 6])
        if fb[0].button("Helpful", disabled="rated" in st.session_state):
            st.session_state["rated"] = assistant().feedback(r["run_id"], 1)
            st.rerun()
        if fb[1].button("Not helpful", disabled="rated" in st.session_state):
            st.session_state["rated"] = assistant().feedback(r["run_id"], 0)
            st.rerun()
        with st.expander("Agent trace and guardrails"):
            st.code("\n".join(r["trace"]))
            st.json(r["guardrail"])
with tab_metrics:
    st.json(METRICS.summary())
    st.code(METRICS.render() or "(no requests yet)")
