"""Common exception types for ffsc engine dynamics models."""

class MissingPropertyData(RuntimeError):
    """Raised when Route-A/Route-B data required by a property model is absent."""


class NotImplementedInRouteA(RuntimeError):
    """Raised when a thesis-specified formula requires still-missing coefficients."""
