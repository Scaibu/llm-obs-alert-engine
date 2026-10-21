from dataclasses import dataclass

@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_multiplier: float = 2.0
    initial_interval_ms: int = 1000

    def compute_delay_ms(self, attempt: int) -> int:
        if attempt <= 1:
            return self.initial_interval_ms
        return int(self.initial_interval_ms * (self.backoff_multiplier ** (attempt - 1)))
