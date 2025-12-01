from typing import Dict

def get_protocol(emergency_type: str) -> Dict:
    """
    Looks up the emergency protocol steps for a given emergency type.

    Args:
        emergency_type: A short string describing the emergency type.
                        Examples:
                          - "cardiac_arrest"
                          - "choking"
                          - "possible_stroke"
                          - "anaphylaxis"
                          - "unconscious_but_breathing"

    Returns:
        A dictionary with the pattern:
        {
            "status": "success" | "error",
            "data": {
                "title": str,
                "steps": [str, ...],
                "notes": [str, ...],
                "stop_condition": str
            }
            # OR on error:
            "error_message": str
        }
    """

    PROTOCOLS = {
        "cardiac_arrest": {
            "title": "Suspected Cardiac Arrest (Adult)",
            "steps": [
                "1. Call emergency services immediately (or ask someone nearby to call).",
                "2. Place the person on a firm, flat surface.",
                "3. Begin chest compressions at a rate of 100–120 per minute.",
                "4. Push hard and fast in the center of the chest allowing full recoil.",
                "5. If an AED is available, have someone bring and apply it following the prompts.",
            ],
            "notes": [
                "If you are alone, prioritize calling emergency services on speaker while starting compressions.",
                "Do not stop compressions unless you are too exhausted, someone takes over, or a medical professional tells you to stop.",
            ],
            "stop_condition": "Emergency responders arrive and take over.",
        },
        "choking": {
            "title": "Severe Choking (Adult)",
            "steps": [
                "1. Ask the person if they are choking and if they can speak or cough.",
                "2. If they cannot cough, speak, or breathe, stand behind them.",
                "3. Perform abdominal thrusts (Heimlich maneuver) until the object is expelled.",
                "4. If the person becomes unresponsive, gently lower them to the ground and begin CPR.",
            ],
            "notes": [
                "If they can cough or speak, encourage them to continue coughing.",
                "Do not perform blind finger sweeps in the mouth.",
            ],
            "stop_condition": "Object is expelled and breathing improves, or emergency services arrive.",
        },
        "possible_stroke": {
            "title": "Possible Stroke (FAST Assessment)",
            "steps": [
                "1. Check FACE: Ask them to smile — is one side drooping?",
                "2. Check ARMS: Ask them to raise both arms — does one drift downward?",
                "3. Check SPEECH: Ask them to repeat a simple phrase — is speech slurred or strange?",
                "4. Time: Note the time symptoms started.",
                "5. Call emergency services immediately and describe all symptoms and onset time.",
            ],
            "notes": [
                "Do not give them anything to eat or drink.",
                "Remain with them and monitor breathing and responsiveness.",
            ],
            "stop_condition": "Emergency services arrive and take over.",
        },
        "anaphylaxis": {
            "title": "Suspected Anaphylaxis (Severe Allergic Reaction)",
            "steps": [
                "1. Check for signs: swelling of lips/face, difficulty breathing, hives, dizziness.",
                "2. If an epinephrine auto-injector (EpiPen) is available, assist the person to use it.",
                "3. Call emergency services immediately.",
                "4. Have the person lie down and elevate legs if they feel faint, unless this worsens breathing.",
                "5. If symptoms persist and a second auto-injector is available, it may be used per instructions (usually after 5–15 minutes).",
            ],
            "notes": [
                "Even if symptoms improve after epinephrine, medical evaluation is required.",
                "Do not make the person walk or stand if they feel weak or dizzy.",
            ],
            "stop_condition": "Emergency services arrive and take over.",
        },
        "unconscious_but_breathing": {
            "title": "Unconscious but Breathing (Recovery Position)",
            "steps": [
                "1. Call emergency services and report the situation.",
                "2. Check breathing: look for chest rise, listen near nose/mouth, feel for air.",
                "3. If breathing is normal, place the person in the recovery position on their side.",
                "4. Tilt the head slightly back to keep the airway open.",
                "5. Regularly re-check breathing until help arrives.",
            ],
            "notes": [
                "If at any point breathing stops or becomes abnormal, begin CPR.",
                "If there is suspected spinal injury, move the person carefully.",
            ],
            "stop_condition": "Emergency services arrive and take over.",
        },
    }

    protocol = PROTOCOLS.get(emergency_type)
    if not protocol:
        return {
            "status": "error",
            "error_message": f"Unknown emergency_type: {emergency_type}.",
        }

    return {
        "status": "success",
        "data": protocol,
    }
