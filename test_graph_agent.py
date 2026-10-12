from typing import TypedDict

from agent import (
    MAX_ATTEMPTS,
    fix_code,
    generate_code,
    run_tests,
)
from unittest.mock import patch
import graph_agent


from langgraph.graph import END, START, StateGraph
from test_generator import generate_test_cases



def test_graph_succeeds_on_first_attempt():
    with (
        patch.object(
            graph_agent, "generate_test_cases",
            return_value="assert solution() == 1",
        ),
        patch.object(
            graph_agent, "generate_code",
            return_value="def solution(): return 1",
        ),
        patch.object(
            graph_agent, "run_tests",
            return_value=(True, ""),
        ) as run_tests,
        patch.object(graph_agent, "fix_code") as fix_code,
    ):
        result = graph_agent.solve_task_graph("Return 1")

    assert result["success"] is True
    assert result["attempts"] == 1
    assert len(result["log"]) == 1
    run_tests.assert_called_once()
    fix_code.assert_not_called()


def test_graph_repairs_and_then_succeeds():
    with (
        patch.object(
            graph_agent, "generate_test_cases",
            return_value="assert solution() == 1",
        ),
        patch.object(
            graph_agent, "generate_code",
            return_value="def solution(): return 0",
        ),
        patch.object(
            graph_agent, "run_tests",
            side_effect=[
                (False, "AssertionError"),
                (True, ""),
            ],
        ),
        patch.object(
            graph_agent, "fix_code",
            return_value="def solution(): return 1",
        ) as fix_code,
    ):
        result = graph_agent.solve_task_graph("Return 1")

    assert result["success"] is True
    assert result["attempts"] == 2
    assert len(result["log"]) == 2
    fix_code.assert_called_once()


def test_graph_stops_at_max_attempts():
    with (
        patch.object(
            graph_agent, "generate_test_cases",
            return_value="assert solution() == 1",
        ),
        patch.object(
            graph_agent, "generate_code",
            return_value="def solution(): return 0",
        ),
        patch.object(
            graph_agent, "run_tests",
            return_value=(False, "AssertionError"),
        ) as run_tests,
        patch.object(
            graph_agent, "fix_code",
            return_value="def solution(): return 0",
        ) as fix_code,
    ):
        result = graph_agent.solve_task_graph("Return 1")

    assert result["success"] is False
    assert result["attempts"] == graph_agent.MAX_ATTEMPTS
    assert len(result["log"]) == graph_agent.MAX_ATTEMPTS
    assert run_tests.call_count == graph_agent.MAX_ATTEMPTS

def test_graph_saves_checkpoint():
    from langgraph.checkpoint.memory import InMemorySaver

    checkpointer = InMemorySaver()
    graph = graph_agent.build_graph(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "checkpoint-test"}}

    with (
        patch.object(
            graph_agent,
            "generate_test_cases",
            return_value="assert solution() == 1",
        ),
        patch.object(
            graph_agent,
            "generate_code",
            return_value="def solution(): return 1",
        ),
        patch.object(
            graph_agent,
            "run_tests",
            return_value=(True, ""),
        ),
    ):
        result = graph.invoke(
            {
                "task_description": "Return 1",
                "test_code": "",
                "code": "",
                "execution_output": "",
                "passed": False,
                "attempts": 0,
                "attempts_log": [],
                "success": False,
            },
            config=config,
        )

    checkpoint = checkpointer.get(config)

    assert result["success"] is True
    assert checkpoint is not None
    assert checkpoint["channel_values"]["attempts"] == 1
    assert checkpoint["channel_values"]["success"] is True
