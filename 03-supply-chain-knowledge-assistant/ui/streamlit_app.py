"""Supply Chain Knowledge Assistant - demo UI.   streamlit run ui/streamlit_app.py --server.port 8503"""

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from supplykb import rbac
from supplykb.ingest import ensure_index
from supplykb.observability import METRICS
from supplykb.service import KnowledgeAssistant

EXAMPLES = {
    "Figure (flowchart)": "What should happen if a 2-8 C product is above 8 C for more than 2 hours cumulative?",
    "Figure (network)": "Which hub is served by lane L3 and what packaging does it use?",
    "Table": "Which packaging configuration is used for lane L2?",
    "Record (CSV)": "What is the status of LOT-24117?",
    "Blocked (medical)": "What dose should a patient take of Neuravex?",
}


@st.cache_resource(show_spinner="Loading index...")
def assistant() -> KnowledgeAssistant:
    ensure_index()
    return KnowledgeAssistant()


st.set_page_config(page_title="Supply Chain Knowledge Assistant", layout="wide")
st.title("Supply Chain Knowledge Assistant")
roles, _ = rbac.load_roles()
with st.sidebar:
    role = st.selectbox("Role", list(roles), index=1)
    st.caption(f"{roles[role].description} Clearance: **{roles[role].clearance}**")
    for label, q in EXAMPLES.items():
        if st.button(label, use_container_width=True):
            st.session_state["q"] = q

tab_qa, tab_sum, tab_metrics = st.tabs(["Ask", "Summarize", "Metrics"])
with tab_qa:
    q = st.text_input("Question", key="q")
    if st.button("Ask", type="primary") and q:
        with st.spinner("Retrieving and answering..."):
            st.session_state["r"] = assistant().ask(q, role, "streamlit")
with tab_sum:
    doc = st.selectbox("Document", ["DEV-2026-014", "SOP-CC-001", "SUP-QUAL-2026", "GDP-POL-001"])
    style = st.radio("Style", ["brief", "detailed", "executive"], horizontal=True)
    if st.button("Summarize"):
        with st.spinner("Summarising..."):
            st.session_state["r"] = assistant().ask(f"Summarize {doc}", role, "streamlit", "summarize", doc, style)

r = st.session_state.get("r")
if r:
    st.divider()
    st.caption(f"Task: {r['intent'].get('intent')} | outcome: {r['outcome']} | {r['latency_ms'] / 1000:.1f}s")
    (st.warning if r["outcome"] in ("blocked", "denied", "no_answer") else st.markdown)(r["answer"])
    figures = [c for c in r["citations"] if c["content_type"] == "image" and c.get("image_path")]
    for c in figures[:2]:
        st.image(str(ROOT / c["image_path"]), caption=f"[{c['ref']}] {c['doc_id']} > {c['section']}", width=600)
    if r["citations"]:
        with st.expander("Sources"):
            for c in r["citations"]:
                st.markdown(f"**[{c['ref']}]** `{c['doc_id']}` {c['title']} > *{c['section']}* - {c['content_type']}, "
                            f"{c['classification']}, similarity {c['score']:.2f}")
    with st.expander("Trace and guardrails"):
        st.code("\n".join(r["trace"]))
        st.json(r["guardrail"])
with tab_metrics:
    st.json(METRICS.summary())
