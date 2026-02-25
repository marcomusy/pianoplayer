"""Custom exception hierarchy for pianoplayer."""


class PianoPlayerError(Exception):
    """Base exception for pianoplayer failures."""


class ConversionError(PianoPlayerError):
    """Raised when score conversion/parsing fails."""


class ExternalToolError(PianoPlayerError):
    """Raised when an external tool invocation fails."""


class MissingDependencyError(PianoPlayerError):
    """Raised when an optional dependency is required but not installed."""
