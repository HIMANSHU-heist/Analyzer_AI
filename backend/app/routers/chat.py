from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core import chat_history
from app.core.registry import get_file_context
from app.services.llm_service import get_llm_provider

router = APIRouter()


class ChatRequest(BaseModel):
    file_id: str
    message: str


class ChatResponse(BaseModel):
    file_id: str
    answer: str


SYSTEM_PROMPT_TEMPLATE = """You are an AI Data Scientist assistant embedded in a data analysis tool.
A user has uploaded a dataset. Here is everything you currently know about it:

{schema_summary}

Rules:
- Answer using ONLY the schema/stats info above plus general data science reasoning. Do not invent column names or values that aren't listed.
- If the question needs an actual computation you can't derive from the summary above (e.g. exact correlation value), say so plainly and note that a code-execution step would be needed to get the precise number.
- When relevant, proactively suggest: what analysis to run next, what charts would help, whether this looks like a classification/regression/clustering/time-series problem, and any obvious data quality issues (missing values, outliers, imbalance).
- Keep answers concise and concrete, not generic filler.
"""


def _format_schema_summary(schema_summary: dict) -> str:
    """Turn the raw schema dict (from Step 1's file_loader) into readable text
    for the LLM prompt, instead of dumping raw JSON."""
    lines = []
    lines.append(f"Rows: {schema_summary.get('n_rows', 'unknown')}")
    lines.append(f"Columns: {schema_summary.get('n_columns', 'unknown')}")
    lines.append("Column details:")
    for col in schema_summary.get("columns", []):
        lines.append(
            f"  - {col.get('name')}: dtype={col.get('dtype')}, "
            f"missing={col.get('missing_count', 0)}, "
            f"unique={col.get('unique_count', 'n/a')}, "
            f"sample_values={col.get('sample_values', [])}"
        )
    return "\n".join(lines)


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    context = get_file_context(payload.file_id)
    if not context:
        raise HTTPException(
            status_code=404,
            detail="file_id not found. Upload a file first via /upload.",
        )

    schema_text = _format_schema_summary(context["schema_summary"])
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema_summary=schema_text)

    history = chat_history.get(payload.file_id)

    llm = get_llm_provider()
    try:
        answer = llm.chat(system_prompt, payload.message, history=history)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}")

    chat_history.append(payload.file_id, "user", payload.message)
    chat_history.append(payload.file_id, "assistant", answer)

    return ChatResponse(file_id=payload.file_id, answer=answer)


@router.post("/chat/reset")
def reset_chat(file_id: str):
    chat_history.clear(file_id)
    return {"status": "ok", "message": f"Chat history cleared for {file_id}"}
