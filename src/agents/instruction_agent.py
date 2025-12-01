from google.adk.agents import LlmAgent  
from google.genai import types  
from src.config import DEFAULT_MODEL

def create_instruction_agent() -> LlmAgent:
    """
    Creates an LlmAgent that guides the user through protocol steps.

    It takes context like:
      - the emergency type,
      - the protocol steps,
      - the current step index,
      - the user's last response

    And outputs:
      - next_step_message
      - next_step_index
      - done (bool)
    """

    instruction = """
You are a calm, clear emergency instruction assistant.

You will be given:
- emergency_type: string
- protocol_title: string
- steps: list of step strings in order
- current_step_index: integer index into steps
- user_update: latest short message from the user

Your job:
1. Decide whether we should stay on this step, repeat, or move to the next step.
2. Provide a clear, short instruction message for the user (one or two sentences).
3. Mark done=True only when all steps are completed OR when emergency responders arrive.

IMPORTANT:
- Remain calm, encouraging, and precise.
- Do NOT add medical procedures that are not in the provided steps.
"""

    response_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "next_step_index": types.Schema(type=types.Type.INTEGER),
            "done": types.Schema(type=types.Type.BOOLEAN),
            "next_step_message": types.Schema(type=types.Type.STRING),
        },
        required=["next_step_index", "done", "next_step_message"],
    )

    instruction_agent = LlmAgent(
        model=DEFAULT_MODEL,
        instruction=instruction,
        response_schema=response_schema,
        name="instruction_agent",
    )

    return instruction_agent
