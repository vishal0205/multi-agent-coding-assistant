import os
import time
import subprocess
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from test_generator import generate_test_cases  # our new test generator agent
from logger import save_task_result
from config import get_secret

load_dotenv()
client = genai.Client(api_key=get_secret("GEMINI_API_KEY"))

MAX_ATTEMPTS = 5

def clean_code(raw: str) -> str:
    code = (raw or "").strip()
    code = code.removeprefix("```python").removeprefix("```").removesuffix("```").strip()
    return code

def call_gemini(prompt: str, max_retries: int = 3) -> str:
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            return response.text
        except genai_errors.ServerError as e:
            wait = 2 ** attempt
            print(f"  [API error: {e}. Retrying in {wait}s... ({attempt}/{max_retries})]")
            time.sleep(wait)
    raise RuntimeError("Gemini API failed after multiple retries.")

def generate_code(task_description: str) -> str:
    prompt = f"""You are a Python coding assistant.
Write ONLY the Python code to solve this task. No explanations, no markdown fences.
IMPORTANT: Always name the main function `solution`, regardless of any name mentioned in the task description.

Task: {task_description}
"""
    return clean_code(call_gemini(prompt))

def fix_code(task_description: str, previous_code: str, error_output: str) -> str:
    prompt = f"""You are a Python coding assistant. Your previous solution failed.
IMPORTANT: Always name the main function `solution`, regardless of any name mentioned in the task description.

Task: {task_description}

Previous code : {previous_code}

Error/test output : {error_output}

Write a corrected, complete version of the code. Only output the code, no explanations, no markdown fences.
"""
    return clean_code(call_gemini(prompt))

import shutil

def docker_available() -> bool:
    """Checks if Docker is installed and running (works locally, not on Streamlit Cloud)."""
    return shutil.which("docker") is not None

def run_tests_fallback(solution_code: str, test_code: str) -> tuple[bool, str]:
    """Lighter sandbox for environments without Docker (e.g. Streamlit Cloud).
    Still enforces a timeout so infinite loops can't hang the app."""
    combined = solution_code + "\n\n" + test_code
    temp_path = os.path.join(os.getcwd(), "temp_solution.py")
    with open(temp_path, "w") as f:
        f.write(combined)
    try:
        result = subprocess.run(
            ["python", temp_path],
            capture_output=True, text=True, timeout=10
        )
        passed = result.returncode == 0
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        passed = False
        output = "TIMEOUT: code took too long to run (possible infinite loop)"
    return passed, output

def run_tests(solution_code: str, test_code: str) -> tuple[bool, str]:
    if not docker_available():
        return run_tests_fallback(solution_code, test_code)

    combined = solution_code + "\n\n" + test_code
    temp_path = os.path.join(os.getcwd(), "temp_solution.py")
    with open(temp_path, "w") as f:
        f.write(combined)
    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory", "128m",
                "--cpus", "0.5",
                "-v", f"{temp_path}:/sandbox/temp_solution.py",
                "coding-agent-sandbox"
            ],
            capture_output=True, text=True, timeout=15
        )
        passed = result.returncode == 0
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        passed = False
        output = "TIMEOUT: code took too long to run (possible infinite loop)"
    return passed, output



def solve_task(task_description: str) -> dict:
    """Supervisor agent: gets tests from the test generator agent, then runs the generate -> test -> fix loop."""
    print(f"\n[Supervisor] Requesting test cases from test generator agent...")
    test_code = generate_test_cases(task_description)
    print(f"[Supervisor] Test cases received:\n{test_code}\n")

    attempts_log = []
    code = generate_code(task_description)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        passed, output = run_tests(code, test_code)
        attempts_log.append({"attempt": attempt, "code": code, "test_code": test_code, "passed": passed, "output": output})
        print(f"--- Attempt {attempt} ---")
        print(code)
        print(f"Result: {'PASSED' if passed else 'FAILED'}")
        if not passed:
            print(f"Output: {output.strip()[:300]}")

        if passed:
            return {"success": True, "attempts": attempt, "test_code": test_code, "log": attempts_log}

        code = fix_code(task_description, code, output)

    return {"success": False, "attempts": MAX_ATTEMPTS, "test_code": test_code, "log": attempts_log}

if __name__ == "__main__":
    task_id = "task_01_flatten"
    task = "Write a function called flatten(lst) that flattens a nested list of arbitrary depth into a single flat list."
    result = solve_task(task)
    print(f"\n=== FINAL RESULT: {'SUCCESS' if result['success'] else 'FAILED'} in {result['attempts']} attempt(s) ===")
    save_task_result(task_id, task, result)