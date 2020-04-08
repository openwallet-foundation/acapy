"""Libindy utility functions."""

from indy.anoncreds import generate_nonce


async def generate_pr_nonce():
    """Generate a nonce for a proof request."""
    return await generate_nonce()
