"""Supervisor-facing demo UI.   streamlit run ui/streamlit_app.py"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from plant_assist.ingest import ensure_index
from plant_assist.service import PlantAssistant
from plant_assist.sources import SOURCES

BADGE = {"safety": "red", "maintenance": "blue", "quality": "green", "out_of_scope": "gray"}
EXAMPLES = [
    "How do I replace the main cylinder seal on the HP-200 press?",
    "About 10 gallons of solvent spilled near line 3, what do I do?",
    "Eight points in a row are above the center line on my X-bar chart. Is that a problem?",
    "What PPE is required at the sodium hydroxide parts washer?",
]


@st.cache_resource(show_spinner="Loading knowledge base...")
def assistant() -> PlantAssistant:
    ensure_index()
    return PlantAssistant()


st.set_page_config(page_title="PlantAssist", layout="wide")
st.title("PlantAssist")
st.caption("Answers from " + ", ".join(s.display_name for s in SOURCES.values()) + " - with citations.")

with st.sidebar:
    from plant_assist import rbac

    _roles, _ = rbac.load_roles()
    role = st.selectbox("Role", list(_roles), help="Roles limit which documentation sources can be searched")
    st.caption(f"{_roles[role].description} Sources: {', '.join(_roles[role].sources)} (+ safety always)")
    st.subheader("Try an example")
    for ex in EXAMPLES:
        if st.button(ex, use_container_width=True):
            st.session_state["question"] = ex

question = st.text_input("Ask a question", key="question", placeholder="e.g. How do I clear a jam on CV-3?")
if st.button("Ask", type="primary") and question:
    with st.spinner("Routing and searching documentation..."):
        st.session_state["result"] = assistant().ask(question, channel="streamlit", role=role)
        st.session_state.pop("rated", None)

result = st.session_state.get("result")  # kept across reruns so feedback buttons work
if result:
    route = result["route"]
    primary = route.get("primary_source", result["outcome"])
    cols = st.columns(4)
    cols[0].markdown(f"**Primary source**  \n:{BADGE.get(primary, 'gray')}[{primary}]")
    cols[1].markdown(f"**Searched**  \n{', '.join(result['searched_sources']) or '-'}")
    cols[2].markdown(f"**Confidence**  \n{route.get('confidence', 0):.2f} ({route.get('method', '-')})")
    cols[3].markdown(f"**Grounded**  \n{result['grounded']}  ({result['latency_ms'] / 1000:.1f}s)")

    if result["outcome"] == "blocked":
        st.warning(f"Blocked by guardrail: {result['guardrail'].get('input_category') or 'unsafe answer withheld'}")
    if result["safety_alert"]:
        st.error("Emergency language detected - follow plant emergency procedures first.")
    st.markdown(result["answer"])

    if result["citations"]:
        with st.expander("Sources", expanded=True):
            for c in result["citations"]:
                where = c.get("section_path") or c["section"]
                st.markdown(
                    f"**[{c['ref']}]** `{c['doc_id']}` rev {c['revision']} - {c['title']} > *{where}* "
                    f"({c.get('content_type', 'text')}, similarity {c['score']:.2f})"
                )

    rated = st.session_state.get("rated")
    fb = st.columns([1, 1, 6])
    if fb[0].button("Helpful", disabled=bool(rated)):
        st.session_state["rated"] = assistant().feedback(result["run_id"], 1)
        st.rerun()
    if fb[1].button("Not helpful", disabled=bool(rated)):
        st.session_state["rated"] = assistant().feedback(result["run_id"], 0)
        st.rerun()
    if rated:
        fb[2].caption("Thanks - feedback recorded" + (" in LangSmith" if rated["langsmith"] else " in the audit log"))

    with st.expander("Graph trace and guardrails"):
        st.code("\n".join(result["trace"]), language="text")
        st.json(result["guardrail"])
