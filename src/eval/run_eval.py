import json
import os
import uuid
from dataclasses import asdict
from typing import List, Dict, Any
from src.orchestrator import LifeSaverOrchestrator, LifeSaverContext


EVAL_FILE_PATH = os.path.join(
    os.path.dirname(__file__),
    "eval_scenarios.json"
)


class ScenarioResult:
    """
    Small helper to track evaluation results per scenario.
    """

    def __init__(
        self,
        scenario_id: str,
        expected_type: str,
        predicted_type: str,
        classification_ok: bool,
        expected_phrases: List[str],
        missing_phrases: List[str],
    ) -> None:
        self.scenario_id = scenario_id
        self.expected_type = expected_type
        self.predicted_type = predicted_type
        self.classification_ok = classification_ok
        self.expected_phrases = expected_phrases
        self.missing_phrases = missing_phrases

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "expected_type": self.expected_type,
            "predicted_type": self.predicted_type,
            "classification_ok": self.classification_ok,
            "expected_phrases": self.expected_phrases,
            "missing_phrases": self.missing_phrases,
        }


def load_eval_scenarios() -> List[Dict[str, Any]]:
    """
    Load evaluation scenarios from JSON file.
    """
    with open(EVAL_FILE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def run_single_scenario(
    orchestrator: LifeSaverOrchestrator,
    scenario: Dict[str, Any],
) -> ScenarioResult:
    """
    Run one full scenario:
      - triage
      - a few instruction steps
      - EMT report
      - scoring

    Returns a ScenarioResult.
    """
    session_id = str(uuid.uuid4())
    ctx: LifeSaverContext = orchestrator.start_session(session_id=session_id)

    scenario_id = scenario["id"]
    first_message = scenario["first_message"]
    expected_type = scenario["expected_emergency_type"]
    expected_phrases = scenario.get("expected_actions_include", [])

    print("=" * 70)
    print(f"Scenario: {scenario_id}")
    print(f"Description: {scenario.get('description', '')}")
    print(f"User first message: {first_message}")

    # --- TRIAGE ---
    ctx = orchestrator.triage(ctx, first_message)

    predicted_type = ctx.emergency_type or "unknown"
    classification_ok = (predicted_type == expected_type)

    print(f"Predicted emergency_type: {predicted_type}")
    print(f"Expected emergency_type:  {expected_type}")
    print(f"Classification OK?       {classification_ok}")

    # --- INSTRUCTION LOOPS ---
    for update in scenario.get("user_updates", []):
        print(f"\nUser update: {update}")
        result = orchestrator.next_instruction(ctx, update)
        instr_msg = result["instruction_message"]
        calm_msg = result["calming_message"]
        done = result["done"]

        print(f"Instruction Agent: {instr_msg}")
        print(f"Calming Agent:     {calm_msg}")

        if done:
            print("[Instruction agent marked sequence as done]")
            break

    # --- EMT REPORT ---
    report = orchestrator.generate_emt_report(ctx)
    print("\n=== EMT Report (truncated for console) ===")
    # Just show first ~500 chars in console
    print(report[:500] + ("..." if len(report) > 500 else ""))

    report_lower = report.lower()
    missing_phrases: List[str] = []
    for phrase in expected_phrases:
        if phrase.lower() not in report_lower:
            missing_phrases.append(phrase)

    if missing_phrases:
        print("\nMissing expected phrases in EMT report:")
        for mp in missing_phrases:
            print(f" - {mp}")
    else:
        print("\nAll expected phrases found in EMT report.")

    return ScenarioResult(
        scenario_id=scenario_id,
        expected_type=expected_type,
        predicted_type=predicted_type,
        classification_ok=classification_ok,
        expected_phrases=expected_phrases,
        missing_phrases=missing_phrases,
    )


def summarize_results(results: List[ScenarioResult]) -> None:
    """
    Print a final summary across all scenarios.
    """
    total = len(results)
    correct_classifications = sum(1 for r in results if r.classification_ok)

    print("\n" + "#" * 70)
    print("EVALUATION SUMMARY")
    print("#" * 70)
    print(f"Total scenarios:         {total}")
    print(f"Correct classifications: {correct_classifications}/{total}")

    fully_covered_reports = sum(1 for r in results if len(r.missing_phrases) == 0)
    print(f"Reports with all expected phrases: {fully_covered_reports}/{total}")

    print("\nDetailed results:")
    for r in results:
        print("-" * 70)
        print(f"Scenario: {r.scenario_id}")
        print(f"  Classification OK? {r.classification_ok}")
        print(f"  Expected type:     {r.expected_type}")
        print(f"  Predicted type:    {r.predicted_type}")
        if r.missing_phrases:
            print("  Missing phrases in EMT report:")
            for mp in r.missing_phrases:
                print(f"    - {mp}")
        else:
            print("  EMT report includes all expected phrases.")


def main():
    scenarios = load_eval_scenarios()
    orchestrator = LifeSaverOrchestrator()

    all_results: List[ScenarioResult] = []

    for scenario in scenarios:
        result = run_single_scenario(orchestrator, scenario)
        all_results.append(result)

    summarize_results(all_results)


if __name__ == "__main__":
    main()
