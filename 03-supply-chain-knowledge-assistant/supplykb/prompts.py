"""Versioned prompt templates for question answering and document summarisation.

Templates are LangChain ChatPromptTemplates registered by name + version, so a change to a prompt is a
new version that can be evaluated (eval/run_eval.py, LangSmith experiments) before it becomes the default.
"""

from langchain_core.prompts import ChatPromptTemplate

QA_V1 = ChatPromptTemplate.from_messages([
    ("system",
     ("You are an enterprise knowledge assistant for drug supply-chain and quality teams. Answer ONLY from the "
     "numbered context excerpts. Cite excerpt numbers like [2] after each fact. Figures are described in excerpts "
     "marked [Figure ...]; cite them the same way. Copy numbers, temperatures, lot and document IDs exactly. "
     "If the context does not contain the answer, say 'The documents I can access do not cover this.' "
     "Never give medical or dosing advice.")),
    ("human", "Question: {question}\n\nContext:\n{context}"),
])

SUMMARIZE_V1 = ChatPromptTemplate.from_messages([
    ("system",
     ("You summarise controlled documents for supply-chain and quality teams. Use ONLY the document text provided. "
     "Style: {style_instructions} Copy numbers, dates and IDs exactly. End with 'Source: {doc_id}'.")),
    ("human", "Document {doc_id} - {title}\n\n{document}"),
])

SUMMARY_STYLES = {
    "brief": "3 bullet points: what happened / what the document requires, key numbers, the outcome or decision.",
    "detailed": "short sections: Purpose or Event, Key Facts (with numbers), Decisions / Requirements, Actions.",
    "executive": "4 sentences for a leader: situation, impact, decision, follow-up actions. No jargon.",
}

TEMPLATES = {("qa", "v1"): QA_V1, ("summarize", "v1"): SUMMARIZE_V1}
DEFAULT_VERSIONS = {"qa": "v1", "summarize": "v1"}


def get_template(name: str, version: str | None = None) -> ChatPromptTemplate:
    return TEMPLATES[(name, version or DEFAULT_VERSIONS[name])]
