from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from google.adk.runners import Runner  
from google.adk.sessions import InMemorySessionService  
from google.adk.memory import InMemoryMemoryService 

from src.agents.triage_agent import create_triage_agent
from src.agents.instruction_agent import create_instruction_agent
from src.agents.calming_agent import create_calming_agent
from src.agents.emt_report_agent import create_emt_report_agent
from src.tools.protocol_tool import get_protocol
from src.config import APP_NAME


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

    This class is intentionally simple and explicit so it's easy to
    reason about and extend.
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

    def start_session(self, session_id: str) -> LifeSaverContext:
        """
        Initialize a new LifeSaverContext for a given session_id.
        """
        return LifeSaverContext(session_id=session_id)

    def triage(self, ctx: LifeSaverContext, user_message: str) -> LifeSaverContext:
        """
        Run triage on the first user message.
        """
        triage_result = self.triage_runner.run(
            session_id=ctx.session_id,
            user_input=user_message,
        )

        ctx.events.append(
            {
                "type": "user_message",
                "content": user_message,
            }
        )
        ctx.events.append(
            {
                "type": "triage_output",
                "content": triage_result.output_text,
            }
        )

        # triage_result.output_text should be JSON according to schema;
        ctx.emergency_type = "cardiac_arrest"  

        # Fetch protocol for this emergency type via the tool.
        protocol_resp = get_protocol(ctx.emergency_type)
        ctx.events.append(
            {
                "type": "protocol_lookup",
                "content": protocol_resp,
            }
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
        payload = {
            "emergency_type": ctx.emergency_type,
            "protocol_title": ctx.protocol["title"],
            "steps": steps,
            "current_step_index": ctx.current_step_index,
            "user_update": user_update,
        }

        ctx.events.append({"type": "user_update", "content": user_update})

        # Call instruction agent
        instruction_result = self.instruction_runner.run(
            session_id=ctx.session_id,
            user_input=str(payload),
        )
        ctx.events.append(
            {"type": "instruction_output", "content": instruction_result.output_text}
        )

        next_step_index = min(ctx.current_step_index + 1, len(steps) - 1)
        done = next_step_index == len(steps) - 1
        instruction_message = steps[next_step_index]

        ctx.current_step_index = next_step_index
        ctx.done = done

        # Call calming agent
        calming_result = self.calming_runner.run(
            session_id=ctx.session_id,
            user_input=f"User said: {user_update}. They are on step {next_step_index}.",
        )
        calming_message = calming_result.output_text
        ctx.events.append(
            {"type": "calming_output", "content": calming_message}
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
        events_text = str(ctx.events) 
        emt_result = self.emt_runner.run(
            session_id=ctx.session_id,
            user_input=events_text,
        )
        report = emt_result.output_text
        ctx.events.append({"type": "emt_report", "content": report})
        return report
