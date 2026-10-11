"""Payment Operations Intelligence - demo UI.   streamlit run ui/streamlit_app.py --server.port 8501"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from payops import rbac
from payops.ingest import ensure_index
from payops.observability import METRICS
from payops.service import PaymentOpsAssistant

EXAMPLES = {
    "RCA + recommendation": "Why are vendors being paid twice and what should we do about it?",
    "Trend": "Are duplicate payments increasing since the gateway release?",
    "Summary": "Give leadership a summary of payment operations health",
    "Search": "Find past incidents like a wire rejected for a bad routing number",
    "Blocked (action)": "Release the pending wire for vendor ACME now",
}


@st.cache_resource(show_spinner="Loading index and agents...")
def assistant() -> PaymentOpsAssistant:
    ensure_index()
    return PaymentOpsAssistant()


st.set_page_config(page_title="Payment Ops Intelligence", layout="wide")
st.title("Payment Operations Intelligence")
roles, _ = rbac.load_roles()

with st.sidebar:
    role = st.selectbox("Role", list(roles), help="Roles decide which agents you may use and what data you see")
    st.caption(roles[role].description)
    st.write("Allowed:", ", ".join(roles[role].intents))
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
