from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from src.agents.triage_agent import create_triage_agent
from src.agents.instruction_agent import create_instruction_agent
from src.agents.calming_agent import create_calming_agent
from src.agents.emt_report_agent import create_emt_report_agent
from src.tools.protocol import get_protocol
from src.config import APP_NAME
import json


# ---------------------- Context dataclass ---------------------- #

@dataclass
class LifeSaverContext:
    session_id: str
    emergency_type: Optional[str] = None
    protocol: Optional[Dict[str, Any]] = None
    current_step_index: int = 0
    done: bool = False
    events: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------- Orchestrator --------------------------- #

class LifeSaverOrchestrator:
    """
    High-level orchestrator for the LifeSaver multi-agent workflow.

    - Uses one shared InMemorySessionService.
    - One Runner per agent.
    - You must call `await setup_sessions(user_id, session_id)` ONCE
      before using triage / next_instruction / generate_emt_report.
    """

    def __init__(self) -> None:
        # Shared session service for all runners
        self.session_service = InMemorySessionService()

        # Agents
        self.triage_agent = create_triage_agent()
        self.instruction_agent = create_instruction_agent()
        self.calming_agent = create_calming_agent()
        self.emt_report_agent = create_emt_report_agent()

        # Runners (session_service is REQUIRED)
        self.triage_runner = Runner(
            agent=self.triage_agent,
            app_name=APP_NAME + "_triage",
            session_service=self.session_service,
        )
        self.instruction_runner = Runner(
            agent=self.instruction_agent,
            app_name=APP_NAME + "_instruction",
            session_service=self.session_service,
        )
        self.calming_runner = Runner(
            agent=self.calming_agent,
            app_name=APP_NAME + "_calming",
            session_service=self.session_service,
        )
        self.emt_runner = Runner(
            agent=self.emt_report_agent,
            app_name=APP_NAME + "_emt",
            session_service=self.session_service,
        )

    # ---------- Session setup (call once) ----------

    async def setup_sessions(self, user_id: str, session_id: str) -> None:
        """
        Create ADK sessions for all four runners.

        Call ONCE in the notebook:
            await orchestrator.setup_sessions(user_id=session_id, session_id=session_id)
        """
        app_names = [
            APP_NAME + "_triage",
            APP_NAME + "_instruction",
            APP_NAME + "_calming",
            APP_NAME + "_emt",
        ]

        for app_name in app_names:
            await self.session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
            )

    def start_session(self, session_id: str) -> LifeSaverContext:
        """
        Just returns our high-level context object.
        (Assumes setup_sessions(...) has already been called.)
        """
        return LifeSaverContext(session_id=session_id)

    # ---------- Internal helper: run a Runner synchronously ----------

    def _run_and_get_text(
        self,
        runner: Runner,
        session_id: str,
        content_text: str,
    ) -> str:
        """
        Run an ADK Runner synchronously and return the final text response.

        Uses runner.run(...) (a blocking generator), so NO asyncio.run()
        in the notebook – avoids nested event loop issues.
        """
        content = types.Content(
            role="user",
            parts=[types.Part(text=content_text)],
        )

        final_text = ""

        for event in runner.run(
            user_id=session_id,
            new_message=content,
        ):

            if event.is_final_response() and event.content and event.content.parts:
                part_text = event.content.parts[0].text or ""
                if part_text:
                    final_text = part_text

        return final_text

    # ---------- Public workflow steps ----------

    def triage(self, ctx: LifeSaverContext, user_message: str) -> LifeSaverContext:
        """
        Run triage on the first user message.
        """
        ctx.events.append({"type": "user_message", "content": user_message})

        triage_text = self._run_and_get_text(
            runner=self.triage_runner,
            session_id=ctx.session_id,
            content_text=user_message,
        )

        ctx.events.append(
            {"type": "triage_output_raw", "content": triage_text}
        )

        # Parse JSON from the triage agent
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
            {"type": "triage_output_parsed", "content": triage_json}
        )

        ctx.emergency_type = triage_json.get("emergency_type") or "unconscious_but_breathing"

        # Fetch protocol for this emergency type via our tool
        protocol_resp = get_protocol(ctx.emergency_type)
        ctx.events.append(
            {"type": "protocol_lookup", "content": protocol_resp}
        )

        if protocol_resp["status"] != "success":
            raise RuntimeError(f"Protocol lookup failed: {protocol_resp['error_message']}")

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
        ctx.events.append({"type": "user_update", "content": user_update})

        payload = {
            "emergency_type": ctx.emergency_type,
            "protocol_title": ctx.protocol["title"],
            "steps": steps,
            "current_step_index": ctx.current_step_index,
            "user_update": user_update,
        }

        # Instruction agent call
        instruction_text = self._run_and_get_text(
            runner=self.instruction_runner,
            session_id=ctx.session_id,
            content_text=json.dumps(payload),
        )
        ctx.events.append(
            {"type": "instruction_output_raw", "content": instruction_text}
        )

        # For now, just move to next step in the protocol
        next_step_index = min(ctx.current_step_index + 1, len(steps) - 1)
        done = next_step_index == len(steps) - 1
        instruction_message = steps[next_step_index]

        ctx.current_step_index = next_step_index
        ctx.done = done

        # Calming agent call
        calming_prompt = (
            f"The user said: '{user_update}'. "
            f"They are on step index {next_step_index} "
            f"of protocol '{ctx.protocol['title']}'. "
            "Respond with a short, calm reassurance message."
        )

        calming_message = self._run_and_get_text(
            runner=self.calming_runner,
            session_id=ctx.session_id,
            content_text=calming_prompt,
        )
        ctx.events.append(
            {"type": "calming_output_raw", "content": calming_message}
        )

        if not calming_message or not calming_message.strip():
            calming_message = (
                "You’re doing the right thing. Keep going with the current step; "
                "help is on the way."
            )

        return {
            "instruction_message": instruction_message,
            "calming_message": calming_message,
            "done": ctx.done,
            "ctx": ctx,
        }

    def generate_emt_report(self, ctx: LifeSaverContext) -> str:
        """
        Summarize the entire session as a handoff report.
        """
        events_text = json.dumps(ctx.events, indent=2)
        report = self._run_and_get_text(
            runner=self.emt_runner,
            session_id=ctx.session_id,
            content_text=events_text,
        )
        ctx.events.append({"type": "emt_report", "content": report})
        return report
