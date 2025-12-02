import logging
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
import os
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

from config import CURRENT_POLICY
from prompt import ROUTER_INSTRUCTIONS
from tools import (
    assess_risk,
    generate_image
)

# Environment Check
if not PROJECT_ID or not LOCATION:
    raise EnvironmentError(
        "Missing required environment variables (GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION)."
    )

print(f"Loaded PRIME Config: Project={PROJECT_ID}, Policy Mode={CURRENT_POLICY['mode']}")

async def init_monitoring_state(callback_context: CallbackContext) -> None:
    """
    PRIME Component: M (Monitoring)
    Initializes the audit trail for the current session.
    This runs BEFORE the agent starts thinking.
    """
    invocation_id = callback_context.invocation_id
    
    # Initialize the state to track decisions
    callback_context.state["audit_log"] = {
        "invocation_id": invocation_id,
        "policy_snapshot": CURRENT_POLICY['mode'],
        "risk_score": None,
        "final_action": None
    }
    
    print(f"[PRIME Monitor] Session initialized: {invocation_id}")
    return None

def load_agent() -> LlmAgent:
    """Load the PRIME Safety Router agent."""
    
    agent = LlmAgent(
        name="prime_safety_router",
        model="gemini-2.5-flash-lite",
        description=(
            "You are the PRIME Intervention Router. You act as a safety layer between "
            "users and generative tools. You detect risk, enforce policy, and route actions."
        ),
        instruction=ROUTER_INSTRUCTIONS, # Loaded from prompt.py
        tools=[
            # PRIME Component: R (Risk Sensing)
            assess_risk,
            # Downstream Capability
            generate_image,
        ],
        before_agent_callback=init_monitoring_state,
        
    )

    return agent

root_agent = load_agent()