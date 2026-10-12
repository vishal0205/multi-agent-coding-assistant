import time
from typing import TypedDict
from agent import MAX_ATTEMPTS, fix_code, generate_code, run_tests
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from test_generator import generate_test_cases

class CodingAgentState(TypedDict):
    task_description: str
    test_code: str
    code: str
    execution_output: str
    passed: bool
    attempts: int
    attempts_log: list[dict]
    success: bool


def generate_tests_node(state: CodingAgentState) -> dict:
    """Generate independent tests for the coding task."""
    test_code = generate_test_cases(state["task_description"])
    return {"test_code": test_code}


def generate_code_node(state: CodingAgentState) -> dict:
    """Generate the initial Python solution."""
    code = generate_code(state["task_description"])
    return {"code": code}

def execute_code_node(state: CodingAgentState) -> dict:
    """Run the current solution against the generated tests."""
    start_time = time.perf_counter()
    passed, output = run_tests(state["code"], state["test_code"])
    duration_sec = round(time.perf_counter() - start_time, 4)

    attempt = state["attempts"] + 1

    entry = {
        "attempt": attempt,
        "code": state["code"],
        "test_code": state["test_code"],
        "passed": passed,
        "output": output,
        "duration_sec": duration_sec,
    }

    return {
        "passed": passed,
        "execution_output": output,
        "attempts": attempt,
        "attempts_log": state["attempts_log"] + [entry],
        "success": passed,
    }


def repair_code_node(state: CodingAgentState) -> dict:
    """Ask Gemini to repair the current solution after a failed execution."""
    code = fix_code(
        state["task_description"],
        state["code"],
        state["execution_output"],
    )
    return {"code": code}


def route_after_execution(state: CodingAgentState) -> str:
    """Stop on success or at the retry limit; otherwise repair the solution."""
    if state["passed"]:
        return "finish"

    if state["attempts"] >= MAX_ATTEMPTS:
        return "finish"

    return "repair"

def build_graph(checkpointer=None):
    """Build and compile the coding-agent workflow."""
    builder = StateGraph(CodingAgentState)

    builder.add_node("generate_tests", generate_tests_node)
    builder.add_node("generate_code", generate_code_node)
    builder.add_node("execute_code", execute_code_node)
    builder.add_node("repair_code", repair_code_node)

    builder.add_edge(START, "generate_tests")
    builder.add_edge("generate_tests", "generate_code")
    builder.add_edge("generate_code", "execute_code")

    builder.add_conditional_edges(
        "execute_code",
        route_after_execution,
        {
            "repair": "repair_code",
            "finish": END,
        },
    )

    builder.add_edge("repair_code", "execute_code")

    return builder.compile(checkpointer=checkpointer)

def solve_task_graph(task_description: str) -> dict:
    """Run the LangGraph workflow with in-memory checkpointing."""
    task_start_time = time.perf_counter()

    checkpointer = InMemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "coding-task"}}
    initial_state: CodingAgentState = {
        "task_description": task_description,
        "test_code": "",
        "code": "",
        "execution_output": "",
        "passed": False,
        "attempts": 0,
        "attempts_log": [],
        "success": False,
    }

    final_state = graph.invoke(initial_state, config=config)

    return {
        "success": final_state["success"],
        "attempts": final_state["attempts"],
        "test_code": final_state["test_code"],
        "log": final_state["attempts_log"],
        "duration_sec": round(time.perf_counter() - task_start_time, 4),
    }
