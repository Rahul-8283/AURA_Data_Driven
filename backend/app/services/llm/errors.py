DAILY_QUOTA_MARKER = "free-models-per-day"


class LLMUnavailableError(RuntimeError):
    """No LLM provider could answer. Raised instead of substituting placeholder results."""


class LLMQuotaExceeded(LLMUnavailableError):
    """The OpenRouter free-model daily quota is spent and the fallback also failed.
    Retrying cannot succeed until the daily reset, so callers must not retry."""


def is_daily_quota_error(error: BaseException | str) -> bool:
    return DAILY_QUOTA_MARKER in str(error)
