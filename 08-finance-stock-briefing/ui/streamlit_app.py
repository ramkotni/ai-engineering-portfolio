"""Stock Briefing Assistant - demo UI.   streamlit run ui/streamlit_app.py --server.port 8508"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stockbrief import rbac
from stockbrief.config import get_settings
from stockbrief.ingest import ensure_index
from stockbrief.observability import METRICS
from stockbrief.service import BriefingService

QUESTIONS = {
    "Risk factor": "What share of Northwind's revenue came from its three largest customers?",
    "10-Q update": "What new tariff took effect in May 2026 for NWRB and what is the expected impact?",
    "8-K event": "What were the HLX-INS7 Phase 3 topline results?",
    "Blocked (advice)": "Should my client buy HLXB before the BLA?",
}


@st.cache_resource(show_spinner="Loading filings index...")
def service() -> BriefingService:
    ensure_index()
    return BriefingService()


st.set_page_config(page_title="Stock Briefing Assistant", layout="wide")
st.title("Stock Briefing Assistant")
st.caption("Get up to speed on a stock before a client conversation: current quote, key financials and a cited summary of recent "
           "SEC filings. Informational only - not investment advice.")
roles, _ = rbac.load_roles()
with st.sidebar:
    role = st.selectbox("Role", list(roles))
    r_ = roles[role]
    st.caption(f"{r_.description}\n\nTasks: {', '.join(r_.tasks)} | live data: {'yes' if r_.live_data else 'no'}")
    live = st.toggle("Live data (Yahoo Finance + SEC EDGAR)", value=False,
                     help="Any US ticker. Needs SEC_USER_AGENT in .env for filings; first briefing of a ticker downloads and indexes its filings.")
    if live and not get_settings().sec_user_agent.strip():
        st.warning("SEC_USER_AGENT is not set in .env - live filings are unavailable (quotes still work).")
    source = "live" if live else "synthetic"

tab_brief, tab_ask, tab_metrics = st.tabs(["Briefing", "Ask the filings", "Metrics"])
with tab_brief:
    c1, c2, c3 = st.columns([3, 1, 1])
    company = c1.text_input("Ticker or company", "NWRB", help="Synthetic: NWRB, HLXB. Live: any US-listed ticker, e.g. MSFT")
    go = c2.button("Generate briefing", type="primary")
    quote_only = c3.button("Quote only")
    if go:
        with st.spinner("Quote, financials and filings agents running, then writing the briefing (1-3 min on CPU)..."):
            st.session_state["brief"] = service().brief(company, role, source, "streamlit")
    if quote_only:
        st.session_state["brief"] = service().quote(company, role, source, "streamlit")
    r = st.session_state.get("brief")
    if r:
        st.caption(f"{r['task']} | outcome: {r['outcome']} | {r['latency_ms'] / 1000:.1f}s | run {r['run_id'][:8]}")
        if r.get("cached"):
            st.info(f"Reused a briefing created {r['cached']['created']} for the same request and access scope (no LLM call). "
                    "Cache lifetime: BRIEFING_CACHE_HOURS in .env.")
        if r["outcome"] != "answered":
            st.warning(r["answer"])
        else:
            b = r["briefing"]
            q, pm = b.get("quote") or {}, b.get("price_metrics") or {}
            if q:
                st.subheader(f"{b.get('company', {}).get('name', q.get('name', ''))} ({q.get('symbol', '')})")
                m = st.columns(5)
                m[0].metric("Price", f"{pm['price']} {q.get('currency', '')}", f"{pm['change']:+} ({pm['change_pct']:+}%)" if pm.get("change") is not None else None)
                m[1].metric("52-week range", f"{q.get('fifty_two_week_low')} - {q.get('fifty_two_week_high')}")
                m[2].metric("1-year change", f"{pm['one_year_return_pct']}%" if pm.get("one_year_return_pct") is not None else "n/a")
                m[3].metric("Market cap", f"${pm['market_cap_bn']}B" if pm.get("market_cap_bn") else "n/a")
                m[4].metric("P/E (FY EPS)", pm.get("pe_fy") or pm.get("pe_note"))
                st.caption(f"Quote as of {q.get('as_of')} - {q.get('source')}")
                if b.get("weekly_closes"):
                    st.line_chart(pd.DataFrame(b["weekly_closes"]).set_index("date")["close"], height=180)
            if b.get("metrics"):
                mt = b["metrics"]
                st.markdown(f"**FY{mt['fiscal_year']}**: revenue ${mt['revenue_m']:,.1f}M ({mt['revenue_growth_pct']}%), operating margin "
                            f"{mt['operating_margin_pct']}%, net income ${mt['net_income_m']:,.1f}M, diluted EPS {mt['eps_diluted']}")
                fin = b["financials"]["annual"]
                st.dataframe(pd.DataFrame(fin).set_index("fy")[[c for c in ("revenue", "operating_income", "net_income", "eps_diluted", "cash")
                                                                if c in fin[0]]].T, use_container_width=True)
            for heading, bullets in (b.get("sections") or {}).items():
                st.subheader(heading)
                st.markdown("\n".join(f"- {x}" for x in bullets) or "_Not covered by the available filings._")
            for n in b.get("notes", []):
                st.info(n)
            if b.get("removed_statements"):
                with st.expander(f"Compliance review removed {len(b['removed_statements'])} statement(s)"):
                    st.write(b["removed_statements"])
            if b.get("disclaimer"):
                st.caption(b["disclaimer"])
            if r["citations"]:
                with st.expander("Sources"):
                    for c in r["citations"]:
                        link = f" - [filing]({c['url']})" if str(c.get("url", "")).startswith("http") else ""
                        st.markdown(f"**[{c['ref']}]** {c['title']} > *{c['section']}*{link}")
                st.download_button("Download briefing (Markdown)", r["answer"], file_name=f"{company}_briefing.md")
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
    question = st.text_input("Question (name the company or ticker)", key="q")
    if st.button("Ask") and question:
        with st.spinner("Searching the filings..."):
            st.session_state["ask"] = service().ask(question, role, source, "streamlit")
    a = st.session_state.get("ask")
    if a:
        (st.warning if a["outcome"] != "answered" else st.markdown)(a["answer"])
        with st.expander("Sources and trace"):
            for c in a["citations"]:
                st.markdown(f"**[{c['ref']}]** {c['title']} > *{c['section']}*")
            st.code("\n".join(a["trace"]))

with tab_metrics:
    st.json(METRICS.summary())
