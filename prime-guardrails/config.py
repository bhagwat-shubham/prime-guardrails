import os

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# This is the "P" in PRIME. Change this to demonstrate configurability.
CURRENT_POLICY = {
    "mode": "LOOSE",
    "thresholds": {
        "high": 0.7,
        "medium": 0.3
    },
    # NEW: Specific Rules for the 11k Dataset Categories
    "sensitive_topics": {
        "competitors": {
            "action": "REFUSE",
            "instruction": "Do not discuss specific competitors (e.g., Apple, OpenAI). Reply generally."
        },
        "mental_health": {
            "action": "REWRITE",
            "instruction": "Provide a supportive, non-clinical response. Include helpline disclaimer."
        },
        "geopolitical": {
            "action": "REFUSE",
            "instruction": "Decline to comment on active geopolitical conflicts."
        }
    }
}