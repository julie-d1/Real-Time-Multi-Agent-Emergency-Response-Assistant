from typing import Dict, Any 
from google.genai import types  
from google.adk.agents import LlmAgent 
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

CRITICAL RULES:
- Output MUST be valid JSON.
- Do not include any extra text, apologies, or explanations outside the JSON.
"""

    triage_agent = LlmAgent(
        model=DEFAULT_MODEL,
        instruction=instruction,
        name="triage_agent",
    )

    return triage_agent
