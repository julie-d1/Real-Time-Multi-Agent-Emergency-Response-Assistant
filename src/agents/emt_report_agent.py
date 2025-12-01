from typing import List, Dict, Any
from google.adk.agents import LlmAgent  
from src.config import DEFAULT_MODEL

def create_emt_report_agent() -> LlmAgent:
    """
    Agent that receives a structured list of events and produces
    a concise EMT handoff report.
    """

    instruction = """
You are an assistant that summarizes an emergency event for paramedics (EMTs).

You will be given:
- A list of time-ordered events describing the emergency, including:
  - user messages,
  - triage agent outputs,
  - key actions taken (CPR, EpiPen, recovery position, etc.)

Your task:
1. Produce a concise, factual report including:
   - Who is affected (if known)
   - Main symptoms
   - Actions taken (with approximate order)
   - Any medications mentioned
   - Approximate timing (relative, e.g., "after a few minutes")

2. Use short paragraphs or bullet points.

3. Stay neutral, factual, and avoid speculation.
"""
    emt_agent = LlmAgent(
        model=DEFAULT_MODEL,
        instruction=instruction,
        name="emt_report_agent",
    )

    return emt_agent
