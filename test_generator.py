import os
from dotenv import load_dotenv
from groq import Groq
from config import get_secret

load_dotenv()
groq_client = Groq(api_key=get_secret("GROQ_API_KEY"))


def generate_test_cases(task_description: str, num_tests: int = 5) -> str:
    prompt = f"""You are a test-writing assistant. Given a coding task, write exactly {num_tests} Python test cases using plain `assert` statements.

Rules:
- The function being tested is ALWAYS named `solution`, regardless of any other name mentioned in the task.
- Output ONLY assert statements, one per line.
- No function definitions, no explanations, no markdown fences, no comments.
- Include at least one edge case (empty input, boundary value, etc.) if relevant.
- End with a line that prints: print("ALL TESTS PASSED")

Task: {task_description}
"""
    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content or ""
    return clean_test_code(raw)

def clean_test_code(raw: str) -> str:
    code = raw.strip()
    code = code.removeprefix("```python").removeprefix("```").removesuffix("```").strip()
    return code

if __name__ == "__main__":
    task = "Write a function called flatten(lst) that flattens a nested list of arbitrary depth into a single flat list."
    tests = generate_test_cases(task)
    print("=== Generated Test Cases ===")
    print(tests)