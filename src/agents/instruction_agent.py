from google.genai import types  
from google.adk.agents import LlmAgent 
from src.config import DEFAULT_MODEL


def create_instruction_agent() -> LlmAgent:
    """
    Creates an LlmAgent that guides the user through protocol steps.

    It takes context like:
      - the emergency type,
      - the protocol steps,
      - the current step index,
      - the user's last response

    And outputs JSON with:
      - next_step_message: str
      - next_step_index: int
      - done: bool
    """

    instruction = """
You are a calm, clear emergency instruction assistant.

You will be given (as a JSON-like string):
- emergency_type: string
- protocol_title: string
- steps: list of step strings in order
- current_step_index: integer index into steps
- user_update: latest short message from the user

Your job:
1. Decide whether we should stay on this step, repeat, or move to the next step.
2. Provide a clear, short instruction message for the user (one or two sentences).
3. Set done=true only when:
   - all steps are completed, OR
   - emergency responders have arrived and taken over.

You MUST return ONLY a valid JSON object with exactly these fields:
- next_step_index: integer
- done: boolean
- next_step_message: string

Do NOT include any other text before or after the JSON.
"""

    instruction_agent = LlmAgent(
        model=DEFAULT_MODEL,
        instruction=instruction,
        name="instruction_agent",
    )

    return instruction_agent
