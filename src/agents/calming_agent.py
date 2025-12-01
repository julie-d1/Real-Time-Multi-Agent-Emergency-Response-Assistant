from google.adk.agents import LlmAgent 
from src.config import DEFAULT_MODEL

def create_calming_agent() -> LlmAgent:
    """
    Calming agent: gives short, supportive messages to keep user focused.
    """

    instruction = """
You are a brief, supportive emergency coach.

You receive:
- A short description of the user's emotional state and what they are doing.

Your job:
- Respond with ONE OR TWO sentences of calm reassurance.
- Encourage them to keep going with the instructions.
- Avoid giving new medical instructions. Focus only on emotional support.
"""

    calming_agent = LlmAgent(
        model=DEFAULT_MODEL,
        instruction=instruction,
        name="calming_agent",
    )

    return calming_agent
