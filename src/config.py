from google.adk.models.google_llm import Gemini  

APP_NAME = "LifeSaverEmergencyAgent"

DEFAULT_MODEL = Gemini(model="gemini-2.5-flash-lite")

# List of supported emergency types (used by triage + protocol tools)
EMERGENCY_TYPES = [
    "cardiac_arrest",
    "choking",
    "possible_stroke",
    "anaphylaxis",
    "unconscious_but_breathing",
]
