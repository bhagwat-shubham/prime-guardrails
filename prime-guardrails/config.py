import os

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# This is the "P" in PRIME. Change this to demonstrate configurability.
CURRENT_POLICY = {
    "mode": "STRICT", 
    "thresholds": {
        "high": 0.8,   # Above this = REFUSE
        "medium": 0.4  # Above this = REWRITE
    }
}