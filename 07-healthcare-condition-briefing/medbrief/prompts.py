"""Versioned prompt templates (LangChain ChatPromptTemplate). Bump the version when wording changes so evaluation
results and LangSmith traces can be compared per version."""

from langchain_core.prompts import ChatPromptTemplate

BRIEFING_V1 = ChatPromptTemplate.from_messages([
    ("system",
     ("You write structured condition briefings for a health-system strategy team. Use ONLY the numbered evidence. "
      "Cite evidence numbers like [2] after each fact. Copy numbers, trial IDs, drug classes and organisation names exactly. "
      "Never give advice about an individual patient. Write exactly these sections, each with 2-4 one-sentence bullet points starting "
      "with '- ' (never more than 4):\n{headings}\n"
      "If the evidence does not cover a section, write '- Not covered by the available sources.' "
      "Style: {style_instructions}")),
    ("human", "Condition: {condition}\n\nEvidence:\n{evidence}"),
])

QA_V1 = ChatPromptTemplate.from_messages([
    ("system",
     ("You answer follow-up questions from a health-system strategy team using ONLY the numbered context excerpts. "
      "Cite excerpt numbers like [2] after each fact. Figures are described in excerpts marked [Figure ...]; cite them the "
      "same way. Copy numbers, trial IDs and names exactly. If the context does not contain the answer, say "
      "'The sources I can access do not cover this.' Never give advice about an individual patient.")),
    ("human", "Question: {question}\n\nContext:\n{context}"),
])

STYLES = {
    "analyst": "specific and factual - name drug classes, thresholds, trial IDs, phases and sponsors.",
    "executive": "plain language for executives - 2 bullets per section, lead with the implication for the health system.",
    "clinical": "precise clinical terminology - include recommendation classes, evidence levels and thresholds from the evidence.",
}
SECTIONS = ["Executive summary", "Standard of care", "Emerging treatments", "Key companies and institutions"]
STRATEGY_SECTION = "Strategic considerations"
TEMPLATES = {("briefing", "v1"): BRIEFING_V1, ("qa", "v1"): QA_V1}


def get_template(task: str, version: str = "v1") -> ChatPromptTemplate:
    return TEMPLATES[(task, version)]
