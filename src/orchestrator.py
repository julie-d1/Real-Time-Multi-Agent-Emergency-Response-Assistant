from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from google.genai import types

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService

from src.agents.triage_agent import create_triage_agent
from src.agents.instruction_agent import create_instruction_agent
from src.agents.calming_agent import create_calming_agent
from src.agents.emt_report_agent import create_emt_report_agent
from src.tools.protocol import get_protocol
from src.config import APP_NAME

import json


@dataclass
class LifeSaverContext:
    session_id: str
    emergency_type: Optional[str] = None
    protocol: Optional[Dict[str, Any]] = None
    current_step_index: int = 0
    done: bool = False
    events: List[Dict[str, Any]] = field(default_factory=list)


class LifeSaverOrchestrator:
    """
    High-level orchestrator for the LifeSaver multi-agent workflow.
    """

    def __init__(self) -> None:
        # Session + memory services
        self.session_service = InMemorySessionService()
        self.memory_service = InMemoryMemoryService()

        # Core agents
        self.triage_agent = create_triage_agent()
        self.instruction_agent = create_instruction_agent()
        self.calming_agent = create_calming_agent()
        self.emt_report_agent = create_emt_report_agent()

        # Runners
        self.triage_runner = Runner(
            agent=self.triage_agent,
            app_name=APP_NAME + "_triage",
            session_service=self.session_service,
            memory_service=self.memory_service,
        )
        self.instruction_runner = Runner(
            agent=self.instruction_agent,
            app_name=APP_NAME + "_instruction",
            session_service=self.session_service,
            memory_service=self.memory_service,
        )
        self.calming_runner = Runner(
            agent=self.calming_agent,
            app_name=APP_NAME + "_calming",
            session_service=self.session_service,
            memory_service=self.memory_service,
        )
        self.emt_runner = Runner(
            agent=self.emt_report_agent,
            app_name=APP_NAME + "_emt",
            session_service=self.session_service,
            memory_service=self.memory_service,
        )

    def _run_and_get_text(
        self,
        runner: Runner,
        session_id: str,
        content: types.Content,
    ) -> str:
        """
        Call runner.run(...) which yields events, and return the final text
        of the final event (if any).
        """
        last_event_with_text = None

        for event in runner.run(
            user_id=session_id,   
            new_message=content,
        ):
            if getattr(event, "content", None) and event.content.parts:
                last_event_with_text = event

        if last_event_with_text and last_event_with_text.content.parts:
            for part in last_event_with_text.content.parts:
                if hasattr(part, "text") and part.text and part.text != "None":
                    return part.text

        return ""

    def start_session(self, session_id: str) -> LifeSaverContext:
        """
        Initialize a new LifeSaverContext for a given session_id.
        We let ADK handle its own internal session management.
        """
        return LifeSaverContext(session_id=session_id)

    def triage(self, ctx: LifeSaverContext, user_message: str) -> LifeSaverContext:
        """
        Run triage on the first user message.
        """

        triage_content = types.Content(
            role="user",
            parts=[types.Part(text=user_message)],
        )

        triage_text = self._run_and_get_text(
            runner=self.triage_runner,
            session_id=ctx.session_id,
            content=triage_content,
        )

        ctx.events.append({"type": "user_message", "content": user_message})
        ctx.events.append({"type": "triage_output_raw", "content": triage_text})

        try:
            triage_json = json.loads(triage_text)
        except json.JSONDecodeError:
            triage_json = {
                "emergency_type": None,
                "confidence": 0.0,
                "summary": "Failed to parse triage JSON.",
                "red_flags": [],
            }

        ctx.events.append(
            {
                "type": "triage_output_parsed",
                "content": triage_json,
            }
        )

        ctx.emergency_type = triage_json.get("emergency_type")
        if ctx.emergency_type is None:
            # Last-resort fallback to something safe-ish
            ctx.emergency_type = "unconscious_but_breathing"

        # Fetch protocol for this emergency type via the tool.
        protocol_resp = get_protocol(ctx.emergency_type)
        ctx.events.append(
            {
                "type": "protocol_lookup",
                "content": protocol_resp,
            }
        )

        if protocol_resp["status"] != "success":
            raise RuntimeError(
                f"Protocol lookup failed: {protocol_resp['error_message']}"
            )

        ctx.protocol = protocol_resp["data"]
        ctx.current_step_index = 0
        ctx.done = False
        return ctx

    def next_instruction(
        self,
        ctx: LifeSaverContext,
        user_update: str,
    ) -> Dict[str, Any]:
        """
        Advance the protocol by one step (or repeat), based on user's update.

        Returns:
            {
                "instruction_message": str,
                "calming_message": str,
                "done": bool,
                "ctx": LifeSaverContext
            }
        """
        if not ctx.protocol:
            raise RuntimeError("Protocol is not set. Did you forget to run triage()?")

        steps = ctx.protocol["steps"]
        payload = {
            "emergency_type": ctx.emergency_type,
            "protocol_title": ctx.protocol["title"],
            "steps": steps,
            "current_step_index": ctx.current_step_index,
            "user_update": user_update,
        }

        ctx.events.append({"type": "user_update", "content": user_update})

        # --- Instruction agent ---
        instruction_content = types.Content(
            role="user",
            parts=[types.Part(text=json.dumps(payload))],
        )

        instruction_text = self._run_and_get_text(
            runner=self.instruction_runner,
            session_id=ctx.session_id,
            content=instruction_content,
        )

        ctx.events.append(
            {"type": "instruction_output", "content": instruction_text}
        )

        next_step_index = min(ctx.current_step_index + 1, len(steps) - 1)
        done = next_step_index == len(steps) - 1
        instruction_message = steps[next_step_index]

        ctx.current_step_index = next_step_index
        ctx.done = done

        # --- Calming agent ---
        calming_prompt = (
            f"User said: {user_update}. "
            f"They are currently on step index {next_step_index} "
            f"of protocol '{ctx.protocol['title']}'. "
            "Respond with one short, empathetic sentence."
        )

        calming_content = types.Content(
            role="user",
            parts=[types.Part(text=calming_prompt)],
        )

        calming_text = self._run_and_get_text(
            runner=self.calming_runner,
            session_id=ctx.session_id,
            content=calming_content,
        )

        ctx.events.append({"type": "calming_output", "content": calming_text})

        return {
            "instruction_message": instruction_message,
            "calming_message": calming_text,
            "done": ctx.done,
            "ctx": ctx,
        }

    def generate_emt_report(self, ctx: LifeSaverContext) -> str:
        """
        Summarize the entire session as a handoff report.
        """
        events_text = json.dumps(ctx.events, indent=2)

        emt_content = types.Content(
            role="user",
            parts=[types.Part(text=events_text)],
        )

        emt_text = self._run_and_get_text(
            runner=self.emt_runner,
            session_id=ctx.session_id,
            content=emt_content,
        )

        ctx.events.append({"type": "emt_report", "content": emt_text})
        return emt_text
