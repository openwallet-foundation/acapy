"""Database manager module with automatic backend registration."""

# Automatically register backends when the module is imported
# This ensures backends are available in all processes including test workers
try:
    from .databases.backends.backend_registration import register_backends

    register_backends()
except ImportError:
    # Backend registration is optional - some deployments may not need all backends
    pass
