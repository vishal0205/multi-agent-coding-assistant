import json
import os
from datetime import datetime

LOG_DIR = "logs"

def save_task_result(task_id: str, task_description: str, result: dict):
    """Saves a full task result (all attempts, final outcome) as a JSON file."""
    os.makedirs(LOG_DIR, exist_ok=True)

    record = {
        "task_id": task_id,
        "task_description": task_description,
        "timestamp": datetime.now().isoformat(),
        "success": result["success"],
        "attempts_taken": result["attempts"],
        "test_code": result["test_code"],
        "attempts_log": result["log"],
    }

    filepath = os.path.join(LOG_DIR, f"{task_id}.json")
    with open(filepath, "w") as f:
        json.dump(record, f, indent=2)

    print(f"[Logger] Saved result to {filepath}")
    return filepath

def load_all_results() -> list[dict]:
    """Loads every saved task result, for building the benchmark summary later."""
    if not os.path.exists(LOG_DIR):
        return []
    results = []
    for filename in sorted(os.listdir(LOG_DIR)):
        if filename.endswith(".json"):
            with open(os.path.join(LOG_DIR, filename)) as f:
                results.append(json.load(f))
    return results