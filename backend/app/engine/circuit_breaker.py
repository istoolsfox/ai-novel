"""Engine: circuit breaker.

Tracks consecutive chapter failures within a sliding window.
When failures exceed the threshold, the orchestrator should trip
(pause the job with a diagnostic message) instead of continuing.
"""
from typing import Any


class CircuitBreaker:
    """Consecutive-failure circuit breaker.

    Args:
        threshold: Max consecutive failures before tripping.
        window: Sliding window size (tracks last N chapters).
    """

    def __init__(self, threshold: int = 3, window: int = 5) -> None:
        self.threshold = threshold
        self.window = window
        self._results: list[bool] = []  # True=success, False=failure

    def record_failure(self, error: Exception | str | None = None) -> None:
        self._results.append(False)
        if len(self._results) > self.window:
            self._results.pop(0)

    def record_success(self) -> None:
        self._results.append(True)
        if len(self._results) > self.window:
            self._results.pop(0)

    @property
    def consecutive_failures(self) -> int:
        count = 0
        for ok in reversed(self._results):
            if not ok:
                count += 1
            else:
                break
        return count

    @property
    def failure_count(self) -> int:
        return sum(1 for ok in self._results if not ok)

    @property
    def success_count(self) -> int:
        return sum(1 for ok in self._results if ok)

    def should_trip(self) -> bool:
        """Return True if the breaker should trip (consecutive failures >= threshold)."""
        return self.consecutive_failures >= self.threshold

    def should_stop_step(self, step_name: str, error: Exception | str | None = None) -> bool:
        """Per-step stop decision. A single step failure never trips; only chapter-level patterns do."""
        return False

    def reset(self) -> None:
        self._results.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "window": self.window,
            "consecutive_failures": self.consecutive_failures,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "should_trip": self.should_trip(),
        }
