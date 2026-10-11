"""Condition Briefing Assistant - demo UI.   streamlit run ui/streamlit_app.py --server.port 8507"""

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from medbrief import rbac
from medbrief.config import get_settings
from medbrief.ingest import ensure_index
from medbrief.observability import METRICS
from medbrief.service import BriefingService

QUESTIONS = {
    "Table (merged across pages)": "What is the target dose of sacubitril/valsartan and which recommendation class applies?",
    "Figure 1 (algorithm)": "When should a patient with HFrEF be considered for CRT-D according to the treatment algorithm?",
    "Figure 2 (chart)": "How many active HFrEF gene therapy programs are there and how many are late-stage?",
    "Registry record": "What is SYN-HF-105 and when does it complete?",
    "Blocked (patient advice)": "Should my father start an SGLT2 inhibitor?",
}


@st.cache_resource(show_spinner="Loading index...")
def service() -> BriefingService:
    ensure_index()
    return BriefingService()


st.set_page_config(page_title="Condition Briefing Assistant", layout="wide")
st.title("Condition Briefing Assistant")
st.caption("Structured briefings for a health-system strategy team: standard of care, emerging treatments, key companies and "
           "institutions. Synthetic sources - not clinical guidance.")
roles, _ = rbac.load_roles()
with st.sidebar:
    role = st.selectbox("Role", list(roles))
    r_ = roles[role]
    st.caption(f"{r_.description}\n\nClearance: **{r_.clearance}** | tasks: {', '.join(r_.tasks)} | live data: {'yes' if r_.live_data else 'no'}")

tab_brief, tab_ask, tab_extract, tab_metrics = st.tabs(["Briefing", "Ask", "Extraction", "Metrics"])
with tab_brief:
    c1, c2 = st.columns([3, 1])
    condition = c1.text_input("Condition", "Heart failure with reduced ejection fraction", help="e.g. HFrEF, CHF, type 2 diabetes; "
                              "with live data any condition (ClinicalTrials.gov)")
    live = c2.toggle("Live trial data", value=False, help="ClinicalTrials.gov API v2 instead of the synthetic registry")
    if st.button("Generate briefing", type="primary"):
        with st.spinner("Section agents gathering evidence, then writing the briefing (1-3 min on CPU)..."):
            st.session_state["brief"] = service().brief(condition, role, "live" if live else "synthetic", "streamlit")
    r = st.session_state.get("brief")
    if r:
        st.caption(f"outcome: {r['outcome']} | {r['latency_ms'] / 1000:.1f}s | run {r['run_id'][:8]}")
        if r.get("cached"):
            st.info(f"Reused a briefing created {r['cached']['created']} for the same request and access scope (no LLM call). "
                    "Cache lifetime: BRIEFING_CACHE_HOURS in .env.")
        if r["outcome"] != "answered":
            st.warning(r["answer"])
        else:
            b = r["briefing"]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Active programs", b["pipeline"]["active_programs"])
            m2.metric("Late-stage", len(b["pipeline"]["late_stage"]))
            m3.metric("Companies", len(b["key_players"]["companies"]))
            m4.metric("Institutions", len(b["key_players"]["institutions"]))
            for heading, bullets in b["sections"].items():
                st.subheader(heading)
                st.markdown("\n".join(f"- {x}" for x in bullets) or "_Not covered by the available sources._")
                if heading == "Emerging treatments" and b["pipeline"]["programs"]:
                    st.dataframe(pd.DataFrame(b["pipeline"]["programs"])[["trial_id", "intervention", "mechanism", "phase", "status",
                                                                          "sponsor", "primary_completion"]], hide_index=True)
                if heading == "Key companies and institutions":
                    k1, k2 = st.columns(2)
                    k1.dataframe(pd.DataFrame(b["key_players"]["companies"])[["name", "active_programs", "most_advanced_phase"]], hide_index=True)
                    k2.dataframe(pd.DataFrame(b["key_players"]["institutions"])[["name", "active_programs", "most_advanced_phase"]], hide_index=True)
            for n in b["notes"]:
                st.info(n)
            st.caption(b["disclaimer"])
            figures = [c for c in r["citations"] if c["content_type"] == "image" and c.get("image_path")]
            for c in figures[:2]:
                st.image(str(ROOT / c["image_path"]), caption=f"[{c['ref']}] {c['doc_id']} > {c['section']}", width=650)
            with st.expander("Sources"):
                for c in r["citations"]:
                    st.markdown(f"**[{c['ref']}]** `{c['doc_id']}` {c['title']} > *{c['section']}* - {c['content_type']}, {c['classification']}")
            st.download_button("Download briefing (Markdown)", r["answer"], file_name="briefing.md")
            c_up, c_down, _ = st.columns([1, 1, 6])
            if c_up.button("👍"):
                service().feedback(r["run_id"], 1)
            if c_down.button("👎"):
                service().feedback(r["run_id"], 0)
        with st.expander("Agent trace and guardrails"):
            st.code("\n".join(r["trace"]))
            st.json(r["guardrail"])

with tab_ask:
    cols = st.columns(len(QUESTIONS))
    for col, (label, q) in zip(cols, QUESTIONS.items()):
        if col.button(label, use_container_width=True):
            st.session_state["q"] = q
    q = st.text_input("Follow-up question", key="q")
    if st.button("Ask") and q:
        with st.spinner("Retrieving and answering..."):
            st.session_state["ask"] = service().ask(q, role, "streamlit")
    a = st.session_state.get("ask")
    if a:
        (st.warning if a["outcome"] != "answered" else st.markdown)(a["answer"])
        for c in [c for c in a["citations"] if c["content_type"] == "image" and c.get("image_path")][:1]:
            st.image(str(ROOT / c["image_path"]), caption=f"[{c['ref']}] {c['doc_id']}", width=600)
        with st.expander("Sources and trace"):
            for c in a["citations"]:
                st.markdown(f"**[{c['ref']}]** `{c['doc_id']}` > *{c['section']}* - {c['content_type']}")
            st.code("\n".join(a["trace"]))

with tab_extract:
    st.markdown("How each source document was turned into Markdown before chunking (see docs/DESIGN.md section 3).")
    s = get_settings()
    report = json.loads((s.extracted_dir / "extraction_report.json").read_text(encoding="utf-8"))
    visible = {d: rep for d, rep in report.items() if r_.can_see(rep["classification"])}
    doc = st.selectbox("Document", list(visible))
    rep = visible[doc]
    st.json({k: v for k, v in rep.items() if k != "images"})
    pdf = s.data_dir / rep["file"]
    with open(pdf, "rb") as f:
        st.download_button(f"Download original ({rep['file']})", f.read(), file_name=rep["file"])
    left, right = st.columns(2)
    left.markdown("**Extracted Markdown**")
    left.code((s.extracted_dir / "markdown" / f"{doc}.md").read_text(encoding="utf-8"), language="markdown")
    right.markdown("**Extracted images**")
    for img in rep["images"]:
        path = s.extracted_dir / "images" / f"{img['image_id']}.png"
        if path.exists():
            right.image(str(path), caption=f"{img['image_id']} (page {img['page']}) {img['caption_hint']}")

with tab_metrics:
    st.json(METRICS.summary())
