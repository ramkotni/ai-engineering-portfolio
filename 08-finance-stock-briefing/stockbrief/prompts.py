"""Versioned prompt templates (LangChain ChatPromptTemplate)."""

from langchain_core.prompts import ChatPromptTemplate

BRIEFING_V1 = ChatPromptTemplate.from_messages([
    ("system",
     ("You prepare stock briefings that help a financial advisor get up to speed before a client conversation. Use ONLY the "
      "numbered evidence and cite evidence numbers like [3] after each fact. Copy numbers exactly as written in the evidence; "
      "never compute new numbers. Do NOT give buy, sell or hold opinions, price targets or valuation judgements. Write exactly "
      "these sections, each with 2-4 bullet points starting with '- ':\n{headings}\n"
      "If the evidence does not cover a section, write '- Not covered by the available filings.' Style: {style_instructions}")),
    ("human", "Company: {company}\n\nEvidence:\n{evidence}"),
])

QA_V1 = ChatPromptTemplate.from_messages([
    ("system",
     ("You answer an advisor's follow-up question about a company using ONLY the numbered excerpts from its SEC filings. Cite "
      "excerpt numbers like [2]. Copy numbers exactly. If the excerpts do not contain the answer, say 'The filings I can access do "
      "not cover this.' Never give buy, sell or hold opinions or price targets.")),
    ("human", "Company: {company}\nQuestion: {question}\n\nExcerpts:\n{context}"),
])

STYLES = {
    "advisor": "plain language an advisor can repeat to a client; short bullets; explain any jargon.",
    "analyst": "precise and specific - segment names, percentages, filing items and dates.",
}
SECTIONS = ["Business overview", "Recent performance", "Key risks", "Recent events", "What to watch"]
TEMPLATES = {("briefing", "v1"): BRIEFING_V1, ("qa", "v1"): QA_V1}


def get_template(task: str, version: str = "v1") -> ChatPromptTemplate:
    return TEMPLATES[(task, version)]
