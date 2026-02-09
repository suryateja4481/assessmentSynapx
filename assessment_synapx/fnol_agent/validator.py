import json
import os
from typing import Dict, Any, List, Optional
from langchain.chat_models import init_chat_model

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file if present

from .extractor import extract_from_file
from .router import build_output


def load_expected_from_jsonl(path: str) -> Dict[str, Any]:
    """Load the first JSON object from a JSONL file (one JSON per line)."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            return json.loads(s)
    return {}


def normalize_value(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).strip()
    if s == "":
        return None
    return s



from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate


def call_llm_reasoning(user_prompt: str) -> str:

    system_prompt_text = (
        "You are an insurance claim assistant. Given extracted fields from a FNOL form, "
        "produce a concise explanation (1 sentence) for the routing decision and note any missing or suspicious fields."
        "just give me 5-6 words in one sentence. do not provide \n for next line"
    )
   
    model = init_chat_model(api_key=os.getenv("GROQ_API_KEY"), model=os.getenv("GROQ_MODEL"), model_provider="groq")
    
    from langchain_core.messages import HumanMessage, SystemMessage
    messages = [
        SystemMessage(content=system_prompt_text),
        HumanMessage(content=user_prompt)
    ]
    response = model.invoke(messages)

    return response.content


def validate(expected_jsonl: str, pdf_path: str) -> Dict[str, Any]:
    expected = load_expected_from_jsonl(expected_jsonl)
    extracted = extract_from_file(pdf_path)

    # remove raw text from extracted before returning or routing; keep only length for reasoning
    raw_text = None
    if isinstance(extracted, dict) and "_raw_text" in extracted:
        raw_text = extracted.pop("_raw_text")

    missing: List[str] = []
    inconsistent: List[str] = []

    # Consider union of keys from expected and extracted labels
    keys = [k for k in set(list(expected.keys()) + list(extracted.keys())) if k != "_raw_text"]

    for k in keys:
        exp = normalize_value(expected.get(k))
        ext = normalize_value(extracted.get(k))
        if exp and not ext:
            missing.append(k)
        elif exp and ext and exp.lower() != ext.lower():
            inconsistent.append(k)

    missing_fields = missing + inconsistent

    # routing
    result = build_output(extracted)
    recommended = result.get("recommendedRoute")

    # Build prompts without embedding raw text
  

    user_prompt = (
        f"Extracted fields: {json.dumps(extracted, indent=2)}\n"
        f"Expected fields (from JSONL): {json.dumps(expected, indent=2)}\n"
        f"Missing fields: {missing}\n"
        f"Inconsistent fields: {inconsistent}\n"
        f"Recommended route (system): {recommended}\n"
        f"Raw text length: {len(raw_text) if raw_text else 0}\n"
        "Provide a short reasoning for the routing decision and enumerate discrepancies."
    )

    reasoning = call_llm_reasoning(user_prompt)

    return {
        "extractedFields": extracted,
        "missingFields": missing_fields,
        "recommendedRoute": recommended,
        "reasoning": reasoning,
        "raw_text_length": len(raw_text) if raw_text else 0,
    }
