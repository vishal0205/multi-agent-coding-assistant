
from unittest.mock import patch

import agent


def test_run_tests_fails_closed_when_docker_is_unavailable():
    with (
        patch.object(agent.shutil, "which", return_value=None),
        patch.object(agent, "run_tests_fallback") as fallback,
    ):
        fallback.return_value = (
            False,
            "SANDBOX ERROR: Docker is unavailable. Generated code was not executed.",
        )

        passed, output = agent.run_tests(
            "def solution(): return 1",
            "assert solution() == 1",
        )

    assert passed is False
    assert "docker" in output.lower()
    fallback.assert_called_once()


def test_run_tests_calls_docker_when_available():
    with (
        patch.object(agent.shutil, "which", return_value="docker"),
        patch.object(agent, "docker_available", return_value=True),
        patch.object(
            agent.subprocess,
            "run",
            return_value=agent.subprocess.CompletedProcess(
                args=["docker", "run"],
                returncode=0,
                stdout="All tests passed",
                stderr="",
            ),
        ) as docker_run,
    ):
        passed, output = agent.run_tests(
            "def solution(): return 1",
            "assert solution() == 1",
        )

    assert passed is True
    assert output == "All tests passed"
    docker_run.assert_called_once()

    command = docker_run.call_args.args[0]
    assert command[0] == "docker"
    assert command[1] == "run"
    assert "--network" in command
    assert "none" in command
    assert "--read-only" in command
    assert "--cap-drop" in command
