from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Callable

from veda_connect.service import get_service


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
_SERVICE_PROVIDER: Callable[[], Any] | None = None


def set_service_provider(provider: Callable[[], Any] | None) -> None:
    global _SERVICE_PROVIDER
    _SERVICE_PROVIDER = provider


def _service():
    if _SERVICE_PROVIDER is not None:
        return _SERVICE_PROVIDER()
    return get_service(BASE_DIR)


def _dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _fail(error: str, error_code: str, *, device: str | None = None, action: str | None = None, **extra: Any) -> str:
    payload: dict[str, Any] = {
        "success": False,
        "error": error,
        "error_code": error_code,
    }
    if device is not None:
        payload["device"] = device
    if action is not None:
        payload["action"] = action
    payload.update(extra)
    return _dump(payload)


def _success(**payload: Any) -> str:
    payload.setdefault("success", True)
    return _dump(payload)


def _normalize_target(parameters: dict[str, Any] | None) -> str:
    params = parameters or {}
    return str(
        params.get("device")
        or params.get("target")
        or params.get("device_id")
        or params.get("name")
        or params.get("query")
        or ""
    ).strip()


def _execute_action_name(parameters: dict[str, Any] | None) -> str:
    params = parameters or {}
    return str(params.get("action") or params.get("command") or "").strip()


def _required_params_for_action(action: str) -> list[str]:
    action = (action or "").strip().lower()
    return {
        "launch_app": ["app_name"],
        "close_app": ["app_name"],
        "open_url": ["url"],
        "capture_screen": [],
        "take_photo": [],
        "clipboard_get": [],
        "clipboard_set": ["text"],
        "send_file": ["file_path"],
        "receive_file": ["destination"],
        "media_play": [],
        "media_pause": [],
        "volume_set": ["value"],
        "notification_list": [],
        "get_battery": [],
        "get_device_info": [],
        "mouse_move": ["x", "y"],
        "keyboard_type": ["text"],
    }.get(action, [])


def _required_capabilities_for_action(action: str) -> list[str]:
    action = (action or "").strip().lower()
    return {
        "launch_app": ["launch_app"],
        "close_app": ["launch_app"],
        "open_url": ["launch_app"],
        "capture_screen": ["screen_capture"],
        "take_photo": ["camera"],
        "clipboard_get": ["clipboard"],
        "clipboard_set": ["clipboard"],
        "send_file": ["files"],
        "receive_file": ["files"],
        "media_play": ["media"],
        "media_pause": ["media"],
        "volume_set": ["media"],
        "notification_list": ["notifications"],
        "get_battery": ["battery"],
        "get_device_info": ["device_info"],
        "mouse_move": ["mouse"],
        "keyboard_type": ["keyboard"],
    }.get(action, [])


def _format_devices(devices: list[dict[str, Any]]) -> str:
    items = []
    for device in devices:
        battery = device.get("battery")
        battery_text = f"{battery}%" if battery is not None else "Unknown"
        items.append({
            "device_id": device.get("device_id", ""),
            "name": device.get("name", "Unknown Device"),
            "platform": device.get("platform", "unknown"),
            "online": bool(device.get("online", False)),
            "battery": battery,
            "battery_text": battery_text,
            "ip_address": device.get("ip_address") or device.get("last_seen_ip", "Unknown"),
            "last_seen": device.get("last_seen", "never"),
        })
    return _dump({"success": True, "count": len(items), "devices": items})


def connect_list_devices(parameters: dict[str, Any] | None = None, player=None, speak=None) -> str:
    try:
        service = _service()
        devices = service.list_devices()
        return _format_devices(devices)
    except Exception as exc:
        return _fail(str(exc), "GATEWAY_UNAVAILABLE", action="connect_list_devices")


def connect_get_device(parameters: dict[str, Any] | None = None, player=None, speak=None) -> str:
    params = parameters or {}
    target = _normalize_target(params)
    if not target:
        return _fail("A device name or id is required.", "MISSING_PARAMETERS", action="connect_get_device")
    try:
        service = _service()
        device = service.get_device(target)
        if not device:
            matches = service.resolve_devices(target)
            if len(matches) == 1:
                device = matches[0]
            elif len(matches) > 1:
                return _dump({
                    "success": False,
                    "error": f"Multiple devices match '{target}'.",
                    "error_code": "AMBIGUOUS_DEVICE",
                    "matches": [item.get("name") or item.get("device_id") for item in matches],
                })
        if not device:
            return _fail(f"Device '{target}' not found.", "DEVICE_NOT_FOUND", device=target, action="connect_get_device")
        return _dump({"success": True, "device": device})
    except Exception as exc:
        return _fail(str(exc), "GATEWAY_UNAVAILABLE", device=target, action="connect_get_device")


def connect_get_status(parameters: dict[str, Any] | None = None, player=None, speak=None) -> str:
    params = parameters or {}
    target = _normalize_target(params)
    try:
        service = _service()
        if not target:
            devices = service.list_devices()
            online_count = sum(1 for d in devices if d.get("online"))
            gateway_info = service.gateway_info()
            return _dump({
                "success": True,
                "gateway": gateway_info,
                "total_devices": len(devices),
                "online_devices": online_count,
            })
        device = service.get_device(target)
        if not device:
            matches = service.resolve_devices(target)
            if len(matches) == 1:
                device = matches[0]
        if not device:
            return _fail(f"Device '{target}' not found.", "DEVICE_NOT_FOUND", device=target, action="connect_get_status")
        return _dump({
            "success": True,
            "device": {
                "device_id": device.get("device_id", ""),
                "name": device.get("name", "Unknown Device"),
                "platform": device.get("platform", "unknown"),
                "online": bool(device.get("online", False)),
                "battery": device.get("battery"),
                "charging": device.get("charging"),
                "last_seen": device.get("last_seen", "never"),
            }
        })
    except Exception as exc:
        return _fail(str(exc), "GATEWAY_UNAVAILABLE", device=target or None, action="connect_get_status")


def connect_get_capabilities(parameters: dict[str, Any] | None = None, player=None, speak=None) -> str:
    params = parameters or {}
    target = _normalize_target(params)
    if not target:
        return _fail("A device name or id is required.", "MISSING_PARAMETERS", action="connect_get_capabilities")
    try:
        service = _service()
        result = service.get_capabilities(target)
        if not result.get("success", False):
            return _dump(result)
        device = result.get("device") or {}
        return _dump({
            "success": True,
            "device": {
                "device_id": device.get("device_id", ""),
                "name": device.get("name", "Unknown Device"),
                "platform": device.get("platform", "unknown"),
                "online": bool(device.get("online", False)),
            },
            "capabilities": list(result.get("capabilities") or []),
            "permissions": list(result.get("permissions") or []),
        })
    except Exception as exc:
        return _fail(str(exc), "GATEWAY_UNAVAILABLE", device=target, action="connect_get_capabilities")


def connect_pair_device(parameters: dict[str, Any] | None = None, player=None, speak=None) -> str:
    params = parameters or {}
    try:
        service = _service()
        pending_id = str(params.get("pending_id") or "").strip()
        if pending_id:
            result = asyncio.run(service.approve_pending_request(pending_id))
            return _dump(result)

        device_name = str(params.get("device_name") or params.get("name") or "Unknown Device").strip()
        platform = str(params.get("platform") or "unknown").strip()
        offer = service.create_pairing_offer(device_name=device_name, platform=platform)
        return _dump({
            "success": True,
            "pairing": offer,
            "message": "Share the pairing code or QR payload with the device agent.",
        })
    except Exception as exc:
        return _fail(str(exc), "GATEWAY_UNAVAILABLE", action="connect_pair_device")


def connect_disconnect_device(parameters: dict[str, Any] | None = None, player=None, speak=None) -> str:
    params = parameters or {}
    target = _normalize_target(params)
    if not target:
        return _fail("A device name or id is required.", "MISSING_PARAMETERS", action="connect_disconnect_device")
    reason = str(params.get("reason") or "Disconnected by Veda").strip()
    try:
        service = _service()
        result = asyncio.run(service.disconnect_device(target, reason=reason))
        return _dump(result)
    except Exception as exc:
        return _fail(str(exc), "GATEWAY_UNAVAILABLE", device=target, action="connect_disconnect_device")


def connect_execute(parameters: dict[str, Any] | None = None, player=None, speak=None) -> str:
    params = dict(parameters or {})
    target = _normalize_target(params)
    action = _execute_action_name(params)
    if not target:
        return _fail("A target device is required.", "MISSING_PARAMETERS", action="connect_execute")
    if not action:
        return _fail("An action name is required.", "MISSING_PARAMETERS", device=target, action="connect_execute")

    command_parameters = dict(params.get("parameters") or {})
    for key, value in params.items():
        if key not in {"device", "target", "device_id", "name", "query", "action", "command", "parameters"}:
            command_parameters.setdefault(key, value)

    missing_params = [key for key in _required_params_for_action(action) if not str(command_parameters.get(key, "")).strip()]
    if action == "launch_app" and not any(
        str(command_parameters.get(key, "")).strip() for key in ("app_name", "package", "package_name")
    ):
        missing_params = ["app_name"]
    if missing_params:
        return _dump({
            "success": False,
            "device": target,
            "action": action,
            "error": f"Missing required parameters: {', '.join(missing_params)}.",
            "error_code": "MISSING_PARAMETERS",
            "missing_parameters": missing_params,
        })

    required_capabilities = _required_capabilities_for_action(action)
    if required_capabilities:
        command_parameters = dict(command_parameters)
        command_parameters["required_capabilities"] = required_capabilities

    try:
        service = _service()
        result = service.route_command(target, action, command_parameters)
        if not isinstance(result, dict):
            return _dump({
                "success": True,
                "device": target,
                "action": action,
                "data": result,
            })

        result.setdefault("device", target)
        result.setdefault("action", action)
        if result.get("success", False):
            if "data" not in result and "result" in result:
                result["data"] = result.pop("result")
            return _dump(result)

        error_code = str(result.get("error_code") or "COMMAND_FAILED")
        if error_code == "DEVICE_OFFLINE":
            result["error"] = result.get("error") or f"Your {target} is currently offline."
        return _dump(result)
    except Exception as exc:
        return _fail(str(exc), "GATEWAY_UNAVAILABLE", device=target, action=action)
