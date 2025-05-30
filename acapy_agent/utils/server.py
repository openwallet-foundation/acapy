"""Utility functions for server operations in an AcaPy agent."""


async def remove_unwanted_headers(
    request,
    response,
) -> None:
    """Remove unwanted headers from the response."""
    response.headers.pop("Server", None)
