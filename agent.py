import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors

from config import get_secret
from logger import save_task_result
from test_generator import generate_test_cases


load_dotenv()

_client = None
MAX_ATTEMPTS = 5

DOCKER_IMAGE = "coding-agent-sandbox:latest"
DOCKER_TIMEOUT_SECONDS = 15
DOCKER_MEMORY_LIMIT = "128m"
DOCKER_CPU_LIMIT = "0.5"
DOCKER_PIDS_LIMIT = 64


def get_client():
    """Create the Gemini client once and reuse it."""
    global _client

    if _client is None:
        _client = genai.Client(api_key=get_secret("GEMINI_API_KEY"))

    return _client


def clean_code(raw: str) -> str:
    """Remove surrounding whitespace and optional Markdown code fences."""
    code = (raw or "").strip()
    code = (
        code.removeprefix("```python")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    return code


def call_gemini(prompt: str, max_retries: int = 3) -> str:
    """Call Gemini, retrying transient server errors with exponential backoff."""
    for attempt in range(1, max_retries + 1):
        try:
            response = get_client().models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
            )
            return response.text
        except genai_errors.ServerError as exc:
            wait = 2**attempt
            print(
                f"  [API error: {exc}. Retrying in {wait}s... "
                f"({attempt}/{max_retries})]"
            )
            time.sleep(wait)

    raise RuntimeError("Gemini API failed after multiple retries.")


def generate_code(task_description: str) -> str:
    """Generate an initial solution using the required solution() interface."""
    prompt = f"""You are a Python coding assistant.

Write ONLY the Python code to solve this task. No explanations, no markdown fences.

IMPORTANT: Always name the main function `solution`, regardless of any name mentioned in the task description.

Task: {task_description}
"""
    return clean_code(call_gemini(prompt))


def fix_code(
    task_description: str,
    previous_code: str,
    error_output: str,
) -> str:
    """Ask Gemini to repair a solution that failed its generated tests."""
    prompt = f"""You are a Python coding assistant. Your previous solution failed.

IMPORTANT: Always name the main function `solution`, regardless of any name mentioned in the task description.

Task: {task_description}

Previous code: {previous_code}

Error/test output: {error_output}

Write a corrected, complete version of the code. Only output the code, no explanations, no markdown fences.
"""
    return clean_code(call_gemini(prompt))


def docker_available() -> bool:
    """Return whether Docker is running and the required image is available."""
    docker = shutil.which("docker")
    if docker is None:
        return False

    try:
        daemon = subprocess.run(
            [docker, "info"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if daemon.returncode != 0:
            return False

        image = subprocess.run(
            [docker, "image", "inspect", DOCKER_IMAGE],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return image.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def run_tests_fallback(
    solution_code: str,
    test_code: str,
) -> tuple[bool, str]:
    """Fail closed when Docker is unavailable; never run generated code on the host."""
    return (
        False,
        "SANDBOX ERROR: Docker is unavailable or the sandbox image "
        "cannot be inspected. Generated code was not executed.",
    )


def run_tests(
    solution_code: str,
    test_code: str,
) -> tuple[bool, str]:
    """Run generated code in a restricted Docker container."""
    docker = shutil.which("docker")
    if docker is None or not docker_available():
        return run_tests_fallback(solution_code, test_code)

    combined = f"{solution_code}\n\n{test_code}\n"
    temp_path = None
    container_name = f"coding-agent-{uuid.uuid4().hex[:12]}"

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".py",
            prefix="coding_agent_",
            delete=False,
        ) as temp_file:
            temp_file.write(combined)
            temp_path = Path(temp_file.name).resolve()

        command = [
            docker,
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--memory",
            DOCKER_MEMORY_LIMIT,
            "--memory-swap",
            DOCKER_MEMORY_LIMIT,
            "--cpus",
            DOCKER_CPU_LIMIT,
            "--pids-limit",
            str(DOCKER_PIDS_LIMIT),
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--user",
            "10001:10001",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=16m",
            "--mount",
            (
                f"type=bind,source={temp_path},"
                "target=/sandbox/temp_solution.py,readonly"
            ),
            "--workdir",
            "/sandbox",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            DOCKER_IMAGE,
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=DOCKER_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            try:
                subprocess.run(
                    [docker, "kill", container_name],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                pass

            return (
                False,
                f"TIMEOUT: execution exceeded {DOCKER_TIMEOUT_SECONDS} seconds.",
            )

        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0 and not output.strip():
            output = f"Sandbox container exited with status {result.returncode}."

        return result.returncode == 0, output
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"SANDBOX ERROR: {type(exc).__name__}: {exc}"
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

def solve_task(task_description: str) -> dict:
    """Generate tests, run the solution, and retry failed solutions."""
    print("\n[Supervisor] Requesting test cases from test generator agent...")
    test_code = generate_test_cases(task_description)
    print(f"[Supervisor] Test cases received:\n{test_code}\n")

    attempts_log = []
    code = generate_code(task_description)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        passed, output = run_tests(code, test_code)
        attempts_log.append(
            {
                "attempt": attempt,
                "code": code,
                "test_code": test_code,
                "passed": passed,
                "output": output,
            }
        )

        print(f"--- Attempt {attempt} ---")
        print(code)
        print(f"Result: {'PASSED' if passed else 'FAILED'}")

        if not passed:
            print(f"Output: {output.strip()[:300]}")

        if passed:
            return {
                "success": True,
                "attempts": attempt,
                "test_code": test_code,
                "log": attempts_log,
            }

        # Infrastructure failures cannot be fixed by regenerating code.
        if "SANDBOX ERROR:" in output:
            return {
                "success": False,
                "attempts": attempt,
                "test_code": test_code,
                "log": attempts_log,
                "error": output,
            }

        if attempt < MAX_ATTEMPTS:
            code = fix_code(task_description, code, output)

    return {
        "success": False,
        "attempts": MAX_ATTEMPTS,
        "test_code": test_code,
        "log": attempts_log,
    }

if __name__ == "__main__":
    task_id = "task_01_flatten"
    task = (
        "Write a function called flatten(lst) that flattens a nested list "
        "of arbitrary depth into a single flat list."
    )
    result = solve_task(task)
    status = "SUCCESS" if result["success"] else "FAILED"
    print(
        f"\n=== FINAL RESULT: {status} in "
        f"{result['attempts']} attempt(s) ==="
    )
    save_task_result(task_id, task, result)
