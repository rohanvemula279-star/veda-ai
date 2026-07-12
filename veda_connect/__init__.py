"""Veda Connect subsystem.

This package adds the local gateway, device registry, pairing flow, and
protocol definitions used by Veda AI to reach companion devices.
"""

from .service import VedaConnectService, get_service

__all__ = ["VedaConnectService", "get_service"]
