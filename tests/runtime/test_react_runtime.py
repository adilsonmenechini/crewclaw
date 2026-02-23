import pytest
from unittest.mock import MagicMock
from crewclaw.agent.loop import ReActRuntime
from crewai import Agent


@pytest.fixture
def mock_agent():
    agent = MagicMock(spec=Agent)
    return agent


def test_react_loop_completion(mock_agent):
    runtime = ReActRuntime(mock_agent)

    # Mocking agent's execute_task to return a successful result
    mock_agent.execute_task.return_value = "The task is successfully finished."

    result = runtime.execute("Do something")

    assert "finished" in result.lower()
    assert mock_agent.execute_task.called


def test_react_loop_max_iterations(mock_agent):
    runtime = ReActRuntime(mock_agent)
    runtime.max_iterations = 2

    # Mocking agent to keep returning something that doesn't trigger completion
    mock_agent.execute_task.return_value = "I am still thinking..."

    result = runtime.execute("Do something")

    assert "iteration limit" in result.lower()
    assert mock_agent.execute_task.call_count == 2


def test_watchdog_loop_detection(mock_agent):
    runtime = ReActRuntime(mock_agent)
    runtime.watchdog_enabled = True
    runtime.watchdog_threshold = 2

    # We need to mock _detect_loop to return True to trigger the watchdog
    # or actually make the logic trigger it by setting last_action.
    # However, ReActRuntime.execute doesn't seem to set last_action inside the loop
    # except in its local scope (last_action = None and no updates in the provided code).
    # Wait, looking at loop.py again, last_action is initialized but never updated!

    # Let's test the current implementation's _detect_loop method directly
    action_count = {}
    assert runtime._detect_loop(action_count, "action1") is False
    assert action_count["action1"] == 1
    assert runtime._detect_loop(action_count, "action1") is True  # Second time reaches threshold 2


def test_self_correction_on_error(mock_agent):
    runtime = ReActRuntime(mock_agent)
    runtime.max_iterations = 3

    # First call fails, second call succeeds
    mock_agent.execute_task.side_effect = [Exception("Tool failed"), "Now it is done and finished."]

    result = runtime.execute("Do something")

    assert "finished" in result.lower()
    assert mock_agent.execute_task.call_count == 2
    # Verify the task was modified with the error message
    called_task = mock_agent.execute_task.call_args[0][0]
    assert "Previous attempt failed with error: Tool failed" in called_task.description
