import streamlit as st
import time
from agent import generate_code, fix_code, run_tests, docker_available, MAX_ATTEMPTS
from test_generator import generate_test_cases
from logger import load_all_results

st.set_page_config(page_title="Multi-Agent Coding Assistant", page_icon="🤖", layout="centered")

st.title("Multi-Agent Coding Assistant")
st.caption("Describe a task. A coder agent (Gemini) writes the solution, an independent test generator agent (Groq) writes the tests, and a supervisor loop runs them together — retrying with self-correction until it passes.")

sandbox_mode = "Docker sandbox (full isolation)" if docker_available() else "Timeout-protected fallback (Docker unavailable in this environment)"
st.info(f"Execution mode: {sandbox_mode}")

# --- Example task buttons ---
EXAMPLES = {
    "FizzBuzz": "Write a function called fizzbuzz(n) that returns a list of strings from 1 to n, replacing multiples of 3 with 'Fizz', multiples of 5 with 'Buzz', and multiples of both with 'FizzBuzz'.",
    "Binary Search": "Write a function called binary_search(arr, target) that returns the index of target in a sorted list arr, or -1 if not found.",
    "4Sum (hard)": "Given an array nums of n integers, return an array of all unique quadruplets [a, b, c, d] from nums such that they are distinct indices and a + b + c + d == target. Return no duplicate quadruplets.",
}

st.write("**Try an example:**")
cols = st.columns(len(EXAMPLES))
for col, (label, task_text) in zip(cols, EXAMPLES.items()):
    if col.button(label):
        st.session_state["task_input"] = task_text

task = st.text_area(
    "Describe the coding task",
    key="task_input",
    placeholder="e.g. Write a function called is_prime(n) that returns True if n is a prime number."
)

# --- Solve button with error handling ---
if st.button("Solve", type="primary") and task.strip():
    try:
        with st.status("Generating test cases (test generator agent)...", expanded=True) as status:
            test_code = generate_test_cases(task)
            st.code(test_code, language="python")
            status.update(label="Test cases generated", state="complete")

        code = generate_code(task)
        success = False

        for attempt in range(1, MAX_ATTEMPTS + 1):
            with st.status(f"Attempt {attempt}: running code against tests...", expanded=True) as status:
                st.code(code, language="python")
                passed, output = run_tests(code, test_code)

                if passed:
                    status.update(label=f"Attempt {attempt}: PASSED", state="complete")
                    success = True
                    break
                else:
                    status.update(label=f"Attempt {attempt}: FAILED — retrying", state="error")
                    st.text(output.strip()[:400])
                    code = fix_code(task, code, output)

        st.divider()
        if success:
            st.success(f"Solved in {attempt} attempt(s)")
            st.subheader("Final solution")
            st.code(code, language="python")
        else:
            st.error(f"Could not solve within {MAX_ATTEMPTS} attempts")
            st.subheader("Last attempted solution")
            st.code(code, language="python")

    except Exception as e:
        error_msg = str(e).lower()
        st.divider()
        if "429" in error_msg or "quota" in error_msg or "resource_exhausted" in error_msg:
            st.error("The AI service has hit its free-tier request limit for right now. Please try again in a few minutes.")
        elif "503" in error_msg or "unavailable" in error_msg:
            st.error("The AI service is temporarily overloaded. Please try again in a moment.")
        elif "timeout" in error_msg:
            st.error("The request took too long and timed out. Please try again.")
        else:
            st.error("Something went wrong while processing this task. Please try again, or try a different task description.")
        with st.expander("Technical details (for debugging)"):
            st.text(str(e))

st.divider()
st.subheader("Benchmark results")
st.caption("Precomputed results from a 12-task benchmark of increasing difficulty.")

results = load_all_results()
if results:
    passed = sum(1 for r in results if r["success"])
    avg_attempts = sum(r["attempts_taken"] for r in results) / len(results)
    col1, col2 = st.columns(2)
    col1.metric("Tasks solved", f"{passed}/{len(results)}")
    col2.metric("Avg attempts per task", f"{avg_attempts:.1f}")

    table_data = [
        {"Task": r["task_id"], "Result": "Pass" if r["success"] else "Fail", "Attempts": r["attempts_taken"]}
        for r in results
    ]
    st.table(table_data)
else:
    st.caption("No benchmark results found yet — run run_benchmark.py first.")