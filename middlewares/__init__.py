"""
Модуль middleware.
"""

from middlewares.registration import RegistrationMiddleware
from middlewares.throttle import ThrottleMiddleware

__all__ = [
    "RegistrationMiddleware",
    "ThrottleMiddleware",
]
