"""Query routing and response execution."""

import json
from collections import defaultdict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from src.models.llm_client import llm
from src.prompts.agent_prompts import ROUTER_PROMPT, SUMMARY_INTENT_PROMPT

router_chain = (
    PromptTemplate(template=ROUTER_PROMPT, input_variables=["query"])
    | llm
    | StrOutputParser()
)


def route_query(query: str) -> str:
    decision = router_chain.invoke({"query": query}).strip().lower()
    return "summary" if "summary" in decision else "qa"


def _summary_intent(query: str) -> dict[str, str]:
    fallback = {"type": "full", "granularity": "none", "style": "paragraph"}
    try:
        raw_response = llm.invoke(SUMMARY_INTENT_PROMPT.format(query=query)).content
        response = json.loads(raw_response)
        return {
            key: response.get(key, fallback[key])
            for key in ("type", "granularity", "style")
        }
    except (json.JSONDecodeError, TypeError, AttributeError):
        return fallback


def summarize(documents, query: str) -> str:
    intent = _summary_intent(query)
    grouped = defaultdict(list)

    if intent["granularity"] == "minute":
        for document in documents:
            minute = int(document.metadata["start"] // 60)
            grouped[f"Minute {minute}"].append(document.page_content)
    elif intent["type"] == "section":
        midpoint = max(document.metadata["start"] for document in documents) / 2
        for document in documents:
            section = (
                "First Half"
                if document.metadata["start"] <= midpoint
                else "Second Half"
            )
            grouped[section].append(document.page_content)
    else:
        grouped["Full Video"] = [document.page_content for document in documents]

    context = "\n".join(
        f"{section}:\n{' '.join(parts)}" for section, parts in sorted(grouped.items())
    )
    style = {
        "bullets": "Use bullet points",
        "paragraph": "Write in paragraphs",
        "notes": "Write structured notes",
    }.get(intent["style"], "Write clearly")

    prompt = f"""
Summarize the supplied YouTube transcript.

User request: {query}
Instructions:
- {style}
- Follow the requested structure.
- Do not invent information.

Transcript:
{context}

Answer:
"""
    return llm.invoke(prompt).content
