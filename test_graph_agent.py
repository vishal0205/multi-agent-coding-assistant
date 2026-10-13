from typing import TypedDict
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

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

def test_graph_records_execution_duration():
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
        result = graph_agent.solve_task_graph("Return 1")

    assert result["success"] is True
    assert len(result["log"]) == 1
    assert "duration_sec" in result["log"][0]
    assert isinstance(result["log"][0]["duration_sec"], float)
    assert result["log"][0]["duration_sec"] >= 0

def test_graph_records_total_task_duration():
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
        result = graph_agent.solve_task_graph("Return 1")

    assert result["success"] is True
    assert "duration_sec" in result
    assert isinstance(result["duration_sec"], float)
    assert result["duration_sec"] >= 0

def test_sqlite_checkpoint_survives_reopening_database(tmp_path):
    db_path = tmp_path / "checkpoints.sqlite"
    config = {"configurable": {"thread_id": "persistence-test"}}

    connection = sqlite3.connect(db_path, check_same_thread=False)
    try:
        saver = SqliteSaver(connection)
        saver.setup()

        graph = graph_agent.build_graph(checkpointer=saver)

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

        assert result["success"] is True
        assert saver.get(config) is not None
    finally:
        connection.close()

    reopened_connection = sqlite3.connect(db_path)
    try:
        reopened_saver = SqliteSaver(reopened_connection)
        checkpoint = reopened_saver.get(config)

        assert checkpoint is not None
        assert checkpoint["channel_values"]["attempts"] == 1
        assert checkpoint["channel_values"]["success"] is True
    finally:
        reopened_connection.close()

def test_persistent_solver_returns_result_and_saves_checkpoint(tmp_path):
    db_path = tmp_path / "persistent-solver.sqlite"

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
        result = graph_agent.solve_task_graph_persistent(
            "Return 1",
            task_id="persistent-solver-test",
            db_path=str(db_path),
        )

    assert result["success"] is True
    assert result["attempts"] == 1
    assert result["duration_sec"] >= 0
    assert db_path.exists()

    connection = sqlite3.connect(db_path)
    try:
        saver = SqliteSaver(connection)
        checkpoint = saver.get(
            {"configurable": {"thread_id": "persistent-solver-test"}}
        )
        assert checkpoint is not None
        assert checkpoint["channel_values"]["success"] is True
    finally:
        connection.close()

def test_persistent_solver_isolates_different_task_ids(tmp_path):
    db_path = tmp_path / "isolated-checkpoints.sqlite"

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
        first_result = graph_agent.solve_task_graph_persistent(
            "First task",
            task_id="isolation-task-one",
            db_path=str(db_path),
        )
        second_result = graph_agent.solve_task_graph_persistent(
            "Second task",
            task_id="isolation-task-two",
            db_path=str(db_path),
        )

    assert first_result["success"] is True
    assert second_result["success"] is True

    connection = sqlite3.connect(db_path)
    try:
        saver = SqliteSaver(connection)

        first_checkpoint = saver.get(
            {"configurable": {"thread_id": "isolation-task-one"}}
        )
        second_checkpoint = saver.get(
            {"configurable": {"thread_id": "isolation-task-two"}}
        )

        assert first_checkpoint is not None
        assert second_checkpoint is not None
        assert (
            first_checkpoint["channel_values"]["task_description"]
            == "First task"
        )
        assert (
            second_checkpoint["channel_values"]["task_description"]
            == "Second task"
        )
    finally:
        connection.close()

def test_persistent_solver_repeated_task_id_uses_new_task_input(tmp_path):
    db_path = tmp_path / "repeated-checkpoint.sqlite"

    with (
        patch.object(
            graph_agent,
            "generate_test_cases",
            side_effect=[
                "assert solution() == 1",
                "assert solution() == 2",
            ],
        ),
        patch.object(
            graph_agent,
            "generate_code",
            side_effect=[
                "def solution(): return 1",
                "def solution(): return 2",
            ],
        ),
        patch.object(
            graph_agent,
            "run_tests",
            return_value=(True, ""),
        ),
    ):
        first_result = graph_agent.solve_task_graph_persistent(
            "First task",
            task_id="reused-task-id",
            db_path=str(db_path),
        )
        second_result = graph_agent.solve_task_graph_persistent(
            "Second task",
            task_id="reused-task-id",
            db_path=str(db_path),
        )

    assert first_result["success"] is True
    assert second_result["success"] is True
    assert first_result["test_code"] == "assert solution() == 1"
    assert second_result["test_code"] == "assert solution() == 2"
