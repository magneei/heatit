"""Exceptions for the Heatit API client."""


class HeatitError(Exception):
    """Base exception for Heatit API errors."""


class HeatitAuthError(HeatitError):
    """Authentication failed (invalid credentials or expired token)."""


class HeatitConnectionError(HeatitError):
    """Could not connect to the Heatit API."""


class HeatitResponseError(HeatitError):
    """Unexpected response from the Heatit API."""
