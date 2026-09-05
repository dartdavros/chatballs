"""Backward-compatible default for management commands and local tests.

Runtime services use an explicit surface settings module.
"""

from chatballs_backend.settings_app import *  # noqa: F403
