from unittest.mock import patch

import agent


def test_solve_task_succeeds_on_first_attempt():
    with (
        patch.object(agent, "generate_test_cases", return_value="assert solution() == 1"),
        patch.object(agent, "generate_code", return_value="def solution(): return 1"),
        patch.object(agent, "run_tests", return_value=(True, "")) as run_tests,
        patch.object(agent, "fix_code") as fix_code,
    ):
        result = agent.solve_task("Return 1")

    assert result["success"] is True
    assert result["attempts"] == 1
    assert len(result["log"]) == 1
    run_tests.assert_called_once()
    fix_code.assert_not_called()


def test_solve_task_repairs_and_then_succeeds():
    with (
        patch.object(agent, "generate_test_cases", return_value="assert solution() == 1"),
        patch.object(agent, "generate_code", return_value="def solution(): return 0"),
        patch.object(agent, "run_tests", side_effect=[
            (False, "AssertionError"),
            (True, ""),
        ]),
        patch.object(agent, "fix_code", return_value="def solution(): return 1") as fix_code,
    ):
        result = agent.solve_task("Return 1")

    assert result["success"] is True
    assert result["attempts"] == 2
    assert len(result["log"]) == 2
    fix_code.assert_called_once()


def test_solve_task_stops_after_max_attempts_without_extra_repair():
    with (
        patch.object(agent, "generate_test_cases", return_value="assert solution() == 1"),
        patch.object(agent, "generate_code", return_value="def solution(): return 0"),
        patch.object(agent, "run_tests", return_value=(False, "AssertionError")) as run_tests,
        patch.object(agent, "fix_code", return_value="def solution(): return 0") as fix_code,
    ):
        result = agent.solve_task("Return 1")

    assert result["success"] is False
    assert result["attempts"] == agent.MAX_ATTEMPTS
    assert len(result["log"]) == agent.MAX_ATTEMPTS
    assert run_tests.call_count == agent.MAX_ATTEMPTS
    assert fix_code.call_count == agent.MAX_ATTEMPTS - 1




def test_solve_task_stops_immediately_on_sandbox_error():
    with (
        patch.object(
            agent,
            "generate_test_cases",
            return_value="assert solution() == 1",
        ),
        patch.object(
            agent,
            "generate_code",
            return_value="def solution(): return 1",
        ),
        patch.object(
            agent,
            "run_tests",
            return_value=(
                False,
                "SANDBOX ERROR: Docker is unavailable. Generated code was not executed.",
            ),
        ) as run_tests,
        patch.object(agent, "fix_code") as fix_code,
    ):
        result = agent.solve_task("Return 1")

    assert result["success"] is False
    assert result["attempts"] == 1
    assert len(result["log"]) == 1
    assert "SANDBOX ERROR:" in result["error"]
    run_tests.assert_called_once()
    fix_code.assert_not_called()
