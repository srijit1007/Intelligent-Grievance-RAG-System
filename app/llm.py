
import json
import re

from google import genai
from google.genai import types

from . import config as C


# Priority levels
PRIORITIES = ("low", "medium", "high", "critical")


# Detect urgent complaints
URGENT = re.compile(
    r"fraud|unauthori[sz]ed|hack|stolen|police|legal action|lawyer|chargeback|threat|self.harm",
    re.I
)


# Gemini client
if not C.GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from your .env file")

_client = genai.Client(api_key=C.GEMINI_API_KEY)


# Grievance classification prompt
PROMPT = """You are an intelligent grievance classification assistant.

Analyze the complaint using the provided knowledge base context.

Available categories: {cats}

Rules:
1. Select exactly ONE category from the available categories.
2. Select priority: low, medium, high, or critical.
3. Confidence must be between 0.0 and 1.0.
4. Confidence represents how well the available context supports resolving the complaint.
5. Never invent company policies.
6. Never claim that a refund, replacement, or other action has been completed unless the context confirms it.
7. If the context is insufficient, recommend human review.
8. Return valid JSON only.

Context:
{ctx}

Complaint:
{text}

Required JSON format:
{{
    "category": "one_category_from_the_available_categories",
    "priority": "medium",
    "confidence": 0.85,
    "reply": "A polite and helpful response to the customer."
}}
"""


# Parse Gemini JSON response
def parse(raw: str) -> dict:

    if not raw:
        raise ValueError("Empty Gemini response")

    d = json.loads(raw)

    cat = str(d.get("category", "")).strip().lower()
    pri = str(d.get("priority", "")).strip().lower()

    if cat not in C.CATEGORIES:
        cat = "other"

    if pri not in PRIORITIES:
        pri = "medium"

    confidence = float(d.get("confidence", 0))

    return {
        "category": cat,
        "priority": pri,
        "confidence": max(0.0, min(1.0, confidence)),
        "reply": str(d.get("reply", "")).strip()
    }


# Apply business rules
def apply_rules(res: dict, text: str, best_distance: float) -> dict:

    if URGENT.search(text):
        res["priority"] = "critical"

    res["needs_human"] = (
        res["confidence"] < C.CONFIDENCE_MIN
        or best_distance > C.MAX_DISTANCE
        or res["priority"] == "critical"
    )

    return res


# Gemini grievance classification
def classify(text: str, hits: list) -> dict:

    ctx = "\n---\n".join(h[0] for h in hits) or "(no context)"

    prompt = PROMPT.format(
        ctx=ctx,
        text=text,
        cats=", ".join(C.CATEGORIES)
    )

    for attempt in range(2):

        try:

            response = _client.models.generate_content(
                model=C.LLM_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "You are a professional grievance resolution "
                        "assistant. Return valid JSON only."
                    ),
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=1000
                )
            )

            raw = response.text

            if not raw:
                raise ValueError("Gemini returned an empty response")

            result = parse(raw)

            return apply_rules(
                result,
                text,
                hits[0][1] if hits else 99
            )

        except Exception as e:

            print(
                f"Gemini API Error (attempt {attempt + 1}/2): "
                f"{type(e).__name__}: {e}"
            )

    # Fallback if Gemini fails
    return {
        "category": "other",
        "priority": "high",
        "confidence": 0.0,
        "needs_human": True,
        "reply": (
            "Thank you for contacting us. Your grievance has been "
            "recorded and an agent will follow up shortly."
        )
    }
