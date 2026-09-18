class AppError(Exception):
    """Base exception for application errors."""
    pass

class InvalidScheduleError(AppError):
    """Raised when a schedule is invalid."""
    pass

class LLMUnavailableError(AppError):
    """Raised when the LLM interpreter is unavailable or unconfigured."""
    pass

class OptimizationUnavailableError(AppError):
    """Raised when the energy optimizer is unavailable or unconfigured."""
    pass

class LLMOutputError(AppError):
    """Raised when the LLM outputs an invalid format."""
    pass
