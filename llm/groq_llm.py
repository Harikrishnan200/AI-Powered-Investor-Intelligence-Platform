import os
import re

from groq import Groq
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def get_groq_client() -> Groq:
    """Create Groq client (free-tier LLM API)."""
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


def get_structured_completion(
    prompt: str,
    response_model: type[BaseModel],
    model: str | None = None
) -> BaseModel:
    """
    Generate structured (JSON) output using Groq.

    Args:
        prompt: Input prompt.
        response_model: Pydantic response model.
        model: Groq model name.

    Returns:
        Parsed response model.
    """
    model = model or DEFAULT_MODEL
    client = get_groq_client()

    messages = [
        {
            "role": "system",
            "content": "You are an expert financial analyst. Always respond with valid JSON only."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"}
    )

    text = response.choices[0].message.content
    print("[debug] Raw response:\n", text)

    match = re.search(r"\{.*\}", text, re.S)
    json_text = match.group(0) if match else text

    if json_text.strip() in ("null", "None", ""):
        return response_model.model_construct()

    return response_model.model_validate_json(json_text)
