
import uuid

import streamlit as st

from agent import docker_available
from graph_agent import solve_task_graph_persistent
from logger import load_all_results, save_task_result


st.set_page_config(
    page_title="Multi-Agent Coding Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- Design system ----------
st.markdown(
    """
    <style>
    :root {
        --bg: #101218;
        --panel: #191e28;
        --panel-hover: #202735;
        --border: #303746;
        --text: #f3f5f9;
        --muted: #9ca6b8;
        --blue: #60a5fa;
        --green: #4ade80;
        --red: #fb7185;
    }

    .stApp {
        background: var(--bg);
    }

    .block-container {
        max-width: 1180px;
        padding-top: 2.2rem;
        padding-bottom: 3rem;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    h1, h2, h3 {
        color: var(--text) !important;
        letter-spacing: -0.035em;
    }

    p, label, li {
        color: #d4dae5;
    }

    .eyebrow {
        color: var(--blue);
        font-size: 0.76rem;
        font-weight: 750;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        margin-bottom: 0.55rem;
    }

    .hero-title {
        font-size: clamp(2.1rem, 5vw, 3.3rem);
        line-height: 1.1;
        font-weight: 800;
        letter-spacing: -0.055em;
        color: var(--text);
        margin: 0 0 0.85rem 0;
    }

    .hero-copy {
        color: var(--muted);
        font-size: 1.02rem;
        line-height: 1.7;
        max-width: 760px;
    }

    .panel {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.2rem 1.35rem;
        margin: 0.5rem 0 1rem 0;
    }

    .section-label {
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.65rem;
    }

    .metric-card {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        min-height: 108px;
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.82rem;
        margin-bottom: 0.55rem;
    }

    .metric-value {
        color: var(--text);
        font-size: 1.85rem;
        font-weight: 750;
        line-height: 1.15;
    }

    .metric-note {
        color: var(--muted);
        font-size: 0.76rem;
        margin-top: 0.45rem;
    }

    .workflow {
        display: flex;
        align-items: stretch;
        gap: 0.55rem;
        margin: 1rem 0;
    }

    .workflow-step {
        flex: 1;
        min-width: 0;
        padding: 0.9rem 0.4rem;
        text-align: center;
        border: 1px solid var(--border);
        border-radius: 12px;
        background: var(--panel);
    }

    .workflow-icon {
        font-size: 1.3rem;
        margin-bottom: 0.45rem;
    }

    .workflow-name {
        color: var(--text);
        font-weight: 700;
        font-size: 0.83rem;
    }

    .workflow-detail {
        color: var(--muted);
        font-size: 0.72rem;
        margin-top: 0.25rem;
    }

    .workflow-arrow {
        display: flex;
        align-items: center;
        color: #64748b;
    }

    .tag {
        display: inline-block;
        border: 1px solid #35445b;
        background: #1a2638;
        color: #bfdbfe;
        border-radius: 999px;
        padding: 0.32rem 0.65rem;
        margin: 0.15rem 0.25rem 0.15rem 0;
        font-size: 0.76rem;
    }

    .security-title {
        color: var(--text);
        font-weight: 750;
        margin-bottom: 0.35rem;
    }

    .security-copy {
        color: var(--muted);
        line-height: 1.55;
        font-size: 0.88rem;
    }

    div.stButton > button {
        border-radius: 10px;
        min-height: 2.65rem;
        font-weight: 650;
        transition: border-color 0.15s ease;
    }

    div.stButton > button[kind="primary"] {
        background: #2563eb;
        border: 1px solid #3b82f6;
        color: white;
    }

    div.stButton > button:hover {
        border-color: var(--blue);
    }

    div[data-testid="stTextArea"] textarea {
        background: #171c25;
        border: 1px solid var(--border);
        border-radius: 12px;
        color: var(--text);
        line-height: 1.6;
    }

    div[data-testid="stCode"] {
        border: 1px solid #303746;
        border-radius: 12px;
    }

    div[data-testid="stExpander"] {
        border-color: var(--border);
        border-radius: 10px;
    }

    hr {
        border-color: var(--border);
    }

    .footer-note {
        color: var(--muted);
        font-size: 0.78rem;
        text-align: center;
        padding-top: 1.5rem;
    }

    @media (max-width: 640px) {
        .block-container {
            padding: 1.2rem 1rem 2rem;
        }

        .workflow {
            gap: 0.2rem;
        }

        .workflow-step {
            padding: 0.7rem 0.15rem;
        }

        .workflow-name {
            font-size: 0.68rem;
        }

        .workflow-detail {
            display: none;
        }

        .workflow-icon {
            font-size: 1.05rem;
        }

        .workflow-arrow {
            font-size: 0.7rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Header ----------
st.markdown('<div class="eyebrow">AI ENGINEERING · AGENT SYSTEMS</div>',
            unsafe_allow_html=True)
st.markdown(
    '<div class="hero-title">Multi-Agent Coding Assistant</div>',
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="hero-copy">
        An AI coding workflow where independent agents generate a solution
        and tests, execute them in a restricted sandbox, and use test feedback
        for bounded self-correction.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style="margin:1rem 0 1.4rem 0;">
        <span class="tag">Gemini · Code generation</span>
        <span class="tag">Groq · Test generation</span>
        <span class="tag">LangGraph · Orchestration</span>
        <span class="tag">Docker · Isolation</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------- Benchmark summary ----------
results = [
    result
    for result in load_all_results()
    if result["task_id"].startswith("task_")
]

if results:
    passed_count = sum(1 for result in results if result["success"])
    avg_attempts = sum(
        result["attempts_taken"] for result in results
    ) / len(results)

    metric_columns = st.columns(3)

    metrics = [
        (
            "RECORDED BENCHMARK",
            f"{passed_count}/{len(results)}",
            "Tasks passed in stored results",
        ),
        (
            "AVERAGE ATTEMPTS",
            f"{avg_attempts:.1f}",
            "Across recorded benchmark tasks",
        ),
        (
            "RETRY BUDGET",
            "5",
            "Maximum execution attempts",
        ),
    ]

    for column, (label, value, note) in zip(metric_columns, metrics):
        with column:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.write("")


# ---------- Workflow ----------
st.markdown("### How the system works")

st.markdown(
    """
    <div class="workflow">
        <div class="workflow-step">
            <div class="workflow-icon">⌨️</div>
            <div class="workflow-name">Coder Agent</div>
            <div class="workflow-detail">Gemini</div>
        </div>
        <div class="workflow-arrow">→</div>
        <div class="workflow-step">
            <div class="workflow-icon">🧪</div>
            <div class="workflow-name">Test Generator</div>
            <div class="workflow-detail">Groq</div>
        </div>
        <div class="workflow-arrow">→</div>
        <div class="workflow-step">
            <div class="workflow-icon">🛡️</div>
            <div class="workflow-name">Secure Executor</div>
            <div class="workflow-detail">Restricted Docker</div>
        </div>
        <div class="workflow-arrow">→</div>
        <div class="workflow-step">
            <div class="workflow-icon">↻</div>
            <div class="workflow-name">Self-Correction</div>
            <div class="workflow-detail">Bounded retries</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------- Security status ----------
docker_is_available = docker_available()

if docker_is_available:
    st.success(
        "Secure execution ready · Docker sandbox detected. "
        "Generated code is executed inside the restricted container."
    )
else:
    st.warning(
        "Execution unavailable · Docker is not available in this environment. "
        "Generated code will not be executed. Run locally with Docker enabled "
        "to test solutions."
    )

with st.expander("What security controls are used?"):
    st.markdown(
        """
        When Docker is available, the execution container is configured with
        network access disabled, resource limits, a read-only root filesystem,
        dropped Linux capabilities, and a non-root user.

        If the sandbox cannot be used, the application fails closed rather
        than executing untrusted generated code directly on the host.
        """
    )


# ---------- Coding workspace ----------
st.markdown("### Build and test a solution")
st.caption(
    "Describe the expected behavior. The agents will generate code and tests, "
    "then use execution feedback for bounded repair when available."
)

EXAMPLES = {
    "FizzBuzz": (
        "Write a function called fizzbuzz(n) that returns a list of strings "
        "from 1 to n, replacing multiples of 3 with 'Fizz', multiples of 5 "
        "with 'Buzz', and multiples of both with 'FizzBuzz'."
    ),
    "Binary Search": (
        "Write a function called binary_search(arr, target) that returns "
        "the index of target in a sorted list arr, or -1 if not found."
    ),
    "4Sum · Hard": (
        "Given an array nums of n integers, return an array of all unique "
        "quadruplets [a, b, c, d] from distinct indices where their sum "
        "equals target. Return no duplicate quadruplets."
    ),
}

example_columns = st.columns(len(EXAMPLES))
for column, (label, task_text) in zip(example_columns, EXAMPLES.items()):
    with column:
        if st.button(label, use_container_width=True):
            st.session_state["task_input"] = task_text

task = st.text_area(
    "Describe your coding task",
    key="task_input",
    height=150,
    placeholder=(
        "Example: Write a function is_prime(n) that returns True "
        "if n is prime, otherwise False."
    ),
)

solve_clicked = st.button(
    "Generate and test solution  →",
    type="primary",
    use_container_width=True,
)

if solve_clicked:
    if not task.strip():
        st.warning("Describe a coding task before starting.")
    elif not docker_is_available:
        st.error(
            "The secure execution sandbox is unavailable. "
            "The application will not execute generated code on the host. "
            "Start Docker and verify the sandbox image, then try again."
        )
    else:
        try:
            with st.spinner(
                "Agents are generating code and tests, then running "
                "the secure execution workflow..."
            ):
                task_id = f"ui_{uuid.uuid4().hex[:12]}"
                result = solve_task_graph_persistent(
                    task,
                    task_id=task_id,
                )

            save_task_result(task_id, task, result)

            st.divider()
            st.markdown("### Run results")

            if result["success"]:
                st.success(
                    f"All tests passed in {result['attempts']} attempt(s)."
                )
            elif result.get("error", "").startswith("SANDBOX ERROR:"):
                st.error(
                    "Execution failed because the secure sandbox is unavailable."
                )
                st.caption(result["error"])
            else:
                st.error(
                    f"The task did not pass within "
                    f"{result['attempts']} attempt(s)."
                )

            if result.get("test_code"):
                with st.expander("Generated tests", expanded=True):
                    st.code(result["test_code"], language="python")

            execution_log = result.get("log", [])

            if execution_log:
                st.markdown("### Execution trace")

                for entry in execution_log:
                    status = "PASSED" if entry["passed"] else "FAILED"
                    title = f"Attempt {entry['attempt']} · {status}"

                    with st.expander(
                        title,
                        expanded=(not entry["passed"]),
                    ):
                        st.markdown("**Generated solution**")
                        st.code(entry["code"], language="python")

                        st.markdown("**Execution output**")
                        st.code(entry["output"][:3000] or "(No output)")

                heading = (
                    "Final solution"
                    if result["success"]
                    else "Last attempted solution — not verified"
                )
                st.markdown(f"### {heading}")
                st.code(execution_log[-1]["code"], language="python")

        except Exception as exc:
            error_message = str(exc)
            lowered = error_message.lower()

            st.divider()

            if (
                "429" in lowered
                or "quota" in lowered
                or "resource_exhausted" in lowered
            ):
                st.error(
                    "The AI service has reached its request limit. "
                    "Please wait before trying again."
                )
            elif "503" in lowered or "unavailable" in lowered:
                st.error(
                    "An AI service is temporarily unavailable. "
                    "Please try again later."
                )
            elif "timeout" in lowered:
                st.error("The request timed out. Please try again.")
            else:
                st.error(
                    "The task could not be completed. Review the technical "
                    "details before retrying."
                )

            with st.expander("Technical details"):
                st.code(error_message)


# ---------- Evaluation ----------
st.divider()
st.markdown("### Evaluation")
st.caption(
    "Stored results from the predefined benchmark. These are historical "
    "benchmark records, not a live estimate of general coding accuracy."
)

if results:
    with st.expander("View task-level benchmark results"):
        table_data = [
            {
                "Task": result["task_id"],
                "Result": "Pass" if result["success"] else "Fail",
                "Attempts": result["attempts_taken"],
            }
            for result in results
        ]
        st.dataframe(
            table_data,
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info(
        "No benchmark results found. Run run_benchmark.py to generate "
        "the predefined benchmark results."
    )

st.markdown(
    """
    <div class="footer-note">
        Built with Streamlit · LangGraph · Gemini · Groq · Docker
        <br>
        Secure execution is required to verify generated solutions.
    </div>
    """,
    unsafe_allow_html=True,
)
