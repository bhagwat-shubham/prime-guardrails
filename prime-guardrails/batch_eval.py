import json
import csv
import asyncio
import re
import time
from datetime import datetime

# 1. NEW IMPORTS based on the ADK article
from google.adk.runners import InMemoryRunner
from google.genai import types
from agent import root_agent 

# --- CONFIGURATION ---
INPUT_FILE = "/Users/shubhambhagwat/Desktop/PRIME/prime-guardrails/eval/test_en.json"
OUTPUT_FILE = f"prime_eval_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
CONCURRENCY_LIMIT = 50  # Adjust based on Rate Limits (50 is usually safe for Flash)

# Initialize the Runner ONCE globally
runner = InMemoryRunner(
    agent=root_agent,
    app_name='prime_benchmark',
)

# --- HELPER: RESULT PARSER ---
def parse_agent_response(response_text: str, original_prompt: str):
    """
    Parses the agent's response to extract Status, Answer, and Explanation
    based on the strict ACTION: tags defined in prompt.py.
    """
    clean_text = response_text.strip()
    clean_text_upper = clean_text.upper()
    
    status = "UNKNOWN"
    extracted_answer = ""     # Column for "Option X"
    extracted_content = ""    # Column for Explanation/Reasoning

    # 0. Check for Empty/Blocked Response
    if not clean_text:
        status = "REJECTED_API_BLOCK"
        extracted_content = "Blocked by API Safety Filters (Agent Prompt did not execute)."
        return status, extracted_answer, extracted_content

    # 1. ACTION: REFUSE
    if "ACTION: REFUSE" in clean_text_upper:
        status = "REJECTED"
        match = re.search(r'Reason:\s*(.+)', clean_text, re.IGNORECASE)
        extracted_content = match.group(1).strip() if match else "Refused (No specific reason parsed)"
    
    # 2. ACTION: REWRITE
    elif "ACTION: REWRITE" in clean_text_upper:
        status = "REWRITE"
        match = re.search(r'(?:New Prompt|Rewriting).*?[:|]\s*["\']?(.+?)["\']?$', clean_text, re.IGNORECASE | re.DOTALL)
        extracted_content = match.group(1).strip() if match else clean_text

    # 3. ACTION: ALLOW
    # Format: "ACTION: ALLOW | Choice: Option <X> | Reason: <Text>"
    elif "ACTION: ALLOW" in clean_text_upper:
        status = "APPROVED"
        
        # Extract Choice (Look for text between 'Choice:' and '|')
        choice_match = re.search(r'Choice:\s*(.*?)\s*\|', clean_text, re.IGNORECASE)
        if choice_match:
            extracted_answer = choice_match.group(1).strip()
        else:
            # Fallback regex if pipe is missing but Choice exists
            choice_match_loose = re.search(r'Choice:\s*(.*?)(?:$|\n)', clean_text, re.IGNORECASE)
            if choice_match_loose:
                extracted_answer = choice_match_loose.group(1).strip()

        # Extract Reason (Look for text after 'Reason:')
        reason_match = re.search(r'Reason:\s*(.*)', clean_text, re.IGNORECASE | re.DOTALL)
        if reason_match:
            extracted_content = reason_match.group(1).strip()
        else:
            # Fallback if strict formatting failed completely
            # Remove the "ACTION: ALLOW" tag and keep the rest
            extracted_content = re.sub(r'^ACTION:\s*ALLOW\s*[:|]?\s*', '', clean_text, flags=re.IGNORECASE).strip()

    # 4. Fallback (Legacy/Safety Net)
    else:
        if "refuse" in clean_text.lower() or "cannot generate" in clean_text.lower():
            status = "REJECTED"
            extracted_content = clean_text 
        elif "success" in clean_text.lower() or "generated" in clean_text.lower():
            status = "APPROVED"
            extracted_content = clean_text
        else:
            status = "REJECTED_CHAT" 
            extracted_content = clean_text

    return status, extracted_answer, extracted_content

# --- WORKER: PROCESS SINGLE ENTRY ---
async def process_entry(semaphore, entry, index):
    async with semaphore:
        question_text = entry.get('question', '') 
        options_list = entry.get('options', [])
        
        # Construct Prompt
        if options_list and isinstance(options_list, list):
            formatted_options = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options_list)])
            prompt = f"{question_text}\n\nOptions:\n{formatted_options}"
        else:
            prompt = question_text

        entry_id = entry.get('id', index)
        category = entry.get('category', 'unknown')
        expected_answer = entry.get('answer', '') or entry.get('target', '') or entry.get('label', '')
        
        user_id = f"user_{entry_id}" 

        start_time = time.time()
        full_response_text = ""
        
        try:
            session = await runner.session_service.create_session(
                app_name='prime_benchmark', 
                user_id=user_id
            )

            content = types.Content(
                role='user', 
                parts=[types.Part.from_text(text=prompt)]
            )

            def run_sync_agent():
                accumulated_text = ""
                try:
                    for event in runner.run(
                        user_id=user_id,
                        session_id=session.id,
                        new_message=content,
                    ):
                        if event.content and event.content.parts:
                            for part in event.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    accumulated_text += part.text
                except Exception as loop_e:
                    print(f"  [Warn] Runner loop error for ID {entry_id}: {loop_e}")
                return accumulated_text

            full_response_text = await asyncio.to_thread(run_sync_agent)
            
            # Parse logic
            status, agent_answer, agent_content = parse_agent_response(full_response_text, prompt)
            
        except Exception as e:
            print(f"Error on ID {entry_id}: {e}")
            status = "ERROR"
            agent_answer = ""
            agent_content = str(e)
            full_response_text = str(e)

        latency = round((time.time() - start_time) * 1000)

        return {
            "id": entry_id,
            "category": category,
            "status": status,          
            "latency_ms": latency,
            "original_prompt": prompt,
            "expected_answer": expected_answer,
            "agent_choice": agent_answer,    # Matches 'Choice: ...'
            "agent_explanation": agent_content, # Matches 'Reason: ...'
            "raw_response": full_response_text
        }

# --- MAIN EXECUTION ---
async def main():
    print(f"--- STARTING PRIME EVALUATION (QA MODE) ---")
    print(f"MODE: Full Batch ({INPUT_FILE})")
    print(f"CONCURRENCY: {CONCURRENCY_LIMIT}")

    try:
        with open(INPUT_FILE, 'r') as f: 
            data = json.load(f)
            if not isinstance(data, list):
                print(f"Error: JSON file must contain a list.")
                return
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Failed to parse JSON.")
        return

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = [process_entry(semaphore, item, idx) for idx, item in enumerate(data)]

    print(f"Processing {len(data)} entries...")
    results = []
    
    for f in asyncio.as_completed(tasks):
        result = await f
        results.append(result)
        if len(results) % 50 == 0 or len(results) == len(data):
            print(f"Progress: {len(results)}/{len(data)}")

    # Save to CSV
    keys = ["id", "category", "status", "latency_ms", "original_prompt", "expected_answer", "agent_choice", "agent_explanation", "raw_response"]
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)

    print(f"--- COMPLETED ---")
    print(f"Saved results to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())