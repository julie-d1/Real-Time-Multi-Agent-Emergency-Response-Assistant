from typing import Dict, Any
from google.adk.agents import LlmAgent  
from google.genai import types  
from src.config import DEFAULT_MODEL, EMERGENCY_TYPES


def create_triage_agent() -> LlmAgent:
    """
    Creates an LlmAgent responsible for classifying the emergency type.

    The agent MUST:
      - Pick one emergency_type from EMERGENCY_TYPES
      - Return JSON with fields: emergency_type, confidence, summary, red_flags
    """

    instruction = f"""
You are an emergency triage assistant.

Your job:
1. Read the user's description of a situation.
2. Decide what type of emergency this is, choosing from:
   {EMERGENCY_TYPES}
3. Identify red-flag symptoms mentioned.
4. Return ONLY a valid JSON object with these fields:
   - emergency_type: one of {EMERGENCY_TYPES}
   - confidence: float between 0 and 1
   - summary: short natural language summary
   - red_flags: list of strings

Be concise and do not include any other text besides the JSON.
"""

    response_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "emergency_type": types.Schema(
                type=types.Type.STRING,
                enum=EMERGENCY_TYPES,
            ),
            "confidence": types.Schema(type=types.Type.NUMBER),
            "summary": types.Schema(type=types.Type.STRING),
            "red_flags": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING),
            ),
        },
        required=["emergency_type", "confidence", "summary"],
    )

    triage_agent = LlmAgent(
        model=DEFAULT_MODEL,
        instruction=instruction,
        response_schema=response_schema,
        name="triage_agent",
    )

    return triage_agent
