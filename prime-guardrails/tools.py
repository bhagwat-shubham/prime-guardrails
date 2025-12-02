import json
import os
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError

# Configure the Gemini API (Ensure you have GOOGLE_API_KEY in your env)
# Or use vertexai.init() if you are using Vertex AI
if os.getenv("GOOGLE_API_KEY"):
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def assess_risk(prompt: str) -> dict:
    """
    Analyzes the user prompt for safety risks using a dedicated 'Judge' LLM.
    It evaluates context, not just keywords.
    """
    print(f"   [Tool] 🧠 AI-Scanning prompt: '{prompt}'")
    
    # 1. Use a fast model (Flash) for low latency
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    # 2. The 'Judge' Prompt
    # We force it to return JSON so our code can read it
    judge_prompt = f"""
    You are a Safety Classifier. Analyze the prompt in English or Chinese.
    
    PROMPT: "{prompt}"
    
    1. CATEGORIZE the prompt into one of: [Safe, Violence, Sexual, Competitors, Mental Health, Geopolitical, Other].
    2. SCORE the risk (0.0 - 1.0).
    3. REASONING: Brief explanation.

    Return JSON: {{ "category": "...", "score": <float>, "reason": "..." }}
    """

    try:
        # 3. Get the judgment
        response = model.generate_content(judge_prompt)
        
        # 4. Parse JSON (Handle potential markdown backticks)
        clean_json = response.text.strip().replace("```json", "").replace("```", "")
        result = json.loads(clean_json)
        
        print(f"   [Tool] Result: {result}")
        return result

    except Exception as e:
        print(f"   [Tool] ⚠️ Classification Failed: {e}")
        # Fail-safe: If the Judge breaks, assume High Risk to be safe
        return {"score": 1.0, "reason": "Error in classifier"}

def generate_image(prompt: str):
    """
    Generates the image. In the demo, the Agent only calls this 
    if assess_risk returned a low enough score.
    """
    print(f"   [Tool] 🎨 Generating image for: {prompt}")
    return f"SUCCESS: Image generated for '{prompt}'"