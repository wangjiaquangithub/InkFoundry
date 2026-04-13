"""Tests for Pipeline Controller with circuit breaker."""
import pytest
from Engine.core.controller import PipelineController, CircuitBreakerError


def test_circuit_breaker_triggers():
    ctrl = PipelineController(max_retries=2)

    def failing_task():
        raise ValueError("Fail")

    with pytest.raises(CircuitBreakerError):
        ctrl.execute_with_retry(failing_task)


def test_successful_task():
    ctrl = PipelineController(max_retries=3)

    def success_task():
        return "done"

    result = ctrl.execute_with_retry(success_task)
    assert result == "done"


def test_retry_succeeds_on_second_attempt():
    ctrl = PipelineController(max_retries=3)
    attempts = {"count": 0}

    def flaky_task():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise ValueError("First attempt fails")
        return "success"

    result = ctrl.execute_with_retry(flaky_task)
    assert result == "success"
    assert attempts["count"] == 2


def test_max_retries_exhausted():
    ctrl = PipelineController(max_retries=3)

    def always_fail():
        raise RuntimeError("Always fails")

    with pytest.raises(CircuitBreakerError, match="Max retries"):
        ctrl.execute_with_retry(always_fail)


def test_graceful_degradation():
    """On final retry, controller should return degraded result."""
    ctrl = PipelineController(max_retries=2)

    def always_fail():
        raise RuntimeError("Fails")

    # With graceful_degradation=True, should not raise on last attempt
    result = ctrl.execute_with_retry(always_fail, graceful_degradation=True)
    assert result is not None
    assert result["status"] == "degraded"
