import uuid

def demo_simple_flow():
    """
    Quick-and-dirty demonstration of the LifeSaverOrchestrator.
    Run this locally to sanity check everything is wired correctly.
    """
    orchestrator = LifeSaverOrchestrator()
    session_id = str(uuid.uuid4())

    ctx = orchestrator.start_session(session_id=session_id)

    print("=== LifeSaver Emergency Demo ===")
    first_message = "My dad just collapsed and he's not breathing."
    print(f"User: {first_message}")
    ctx = orchestrator.triage(ctx, first_message)

    # Simulate a couple of instruction loops:
    user_updates = [
        "I'm on the floor next to him.",
        "I'm doing chest compressions like you said.",
        "The ambulance just arrived.",
    ]

    for update in user_updates:
        result = orchestrator.next_instruction(ctx, update)
        instr = result["instruction_message"]
        calm = result["calming_message"]
        done = result["done"]

        print(f"\nUser: {update}")
        print(f"Instruction Agent: {instr}")
        print(f"Calming Agent: {calm}")
        if done:
            print("\n[Instruction sequence marked as done by agent]")
            break

    report = orchestrator.generate_emt_report(ctx)
    print("\n=== EMT Report ===")
    print(report)


if __name__ == "__main__":
    demo_simple_flow()
