"""ZLT S10 router SMS operations and private per-user connection setup."""

from __future__ import annotations

import base64
import hashlib
import http.cookiejar
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from r10n_backend.settings import settings_directory

SERVICE = "r10n:router-sms"
ACCOUNT = "default"


def profile_path() -> Path:
    """Return the per-user router connection profile path."""
    return settings_directory() / "router-sms.json"


def load_profile() -> dict[str, str] | None:
    """Load the non-secret router address and username."""
    try:
        value = json.loads(profile_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(value, dict) or not all(
        isinstance(value.get(k), str) and value[k] for k in ("url", "username")
    ):
        raise ValueError("Invalid router SMS profile; run setup again")
    return {"url": value["url"], "username": value["username"]}


def _keyring() -> Any:
    try:
        import keyring
    except ImportError as error:
        raise RuntimeError("An OS credential store is required for router setup") from error
    if getattr(keyring.get_keyring(), "priority", 0) <= 0:
        raise RuntimeError("An OS credential store is required for router setup")
    return keyring


def save_profile(address: str, username: str, password: str) -> None:
    """Store router details and keep the password in the OS credential service."""
    address = address.strip()
    if "://" not in address:
        address = "http://" + address
    parsed = urllib.parse.urlsplit(address)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Enter a router address such as http://192.168.1.1")
    if not username.strip() or not password:
        raise ValueError("Router username and password are required")
    normalized = f"{parsed.scheme}://{parsed.netloc}"
    ring = _keyring()
    try:
        previous = ring.get_password(SERVICE, ACCOUNT)
        ring.set_password(SERVICE, ACCOUNT, password)
    except Exception as error:
        raise RuntimeError(
            "Could not save the router password in the OS credential service"
        ) from error
    path = profile_path()
    temp: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as f:
            temp = f.name
            json.dump({"url": normalized, "username": username.strip()}, f)
        os.replace(temp, path)
    except Exception:
        if previous is None:
            ring.delete_password(SERVICE, ACCOUNT)
        else:
            ring.set_password(SERVICE, ACCOUNT, previous)
        raise
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)


def decode_message(value: str) -> str:
    """Decode the router's four-hex-digit message representation."""
    if not re.fullmatch(r"(?:[0-9A-Fa-f]{4})*", value):
        raise ValueError("Router returned malformed SMS content")
    return bytes.fromhex(value).decode("utf-16-be", errors="replace").replace("\x00", "")


class RouterClient:
    """A cookie-preserving client for the S10 goform interface."""

    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        )

    def post(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """POST a form and parse a JSON object from the router."""
        request = urllib.request.Request(
            self.url + "/goform/" + endpoint,
            data=urllib.parse.urlencode(params).encode(),
            headers={"Referer": self.url + "/index.html", "X-Requested-With": "XMLHttpRequest"},
        )
        try:
            with self.opener.open(request, timeout=10) as response:
                raw = response.read(2_000_000).decode("utf-8")
            result = json.loads(re.sub(r"[\x00-\x1f]+", "", raw))
        except (OSError, ValueError) as error:
            raise RuntimeError(
                "Could not communicate with the router; check its address and connection"
            ) from error
        if not isinstance(result, dict):
            raise RuntimeError("Router returned an unexpected response")
        return result

    def get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run a router read command."""
        return self.post("goform_get_cmd_process", {"isTest": "false", **params})

    def set(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run a router write command."""
        return self.post("goform_set_cmd_process", {"isTest": "false", **params})

    def login(self, username: str, password: str) -> None:
        """Authenticate once, without automatic password retries."""
        response = self.get({"cmd": "get_token"})
        token = response.get("get_token", response.get("token", ""))
        encoded_user = base64.b64encode(username.encode()).decode()
        digest = hashlib.md5(password.encode(), usedforsecurity=False).hexdigest()
        encoded_password = base64.b64encode(digest.encode()).decode()
        result = self.set(
            {
                "goformId": "LOGIN",
                "username": encoded_user,
                "password": encoded_password,
                "CSRFToken": token,
            }
        )
        if str(result.get("result")) not in {"0", "4"}:
            raise RuntimeError("Router login failed; check the username and password in setup")

    def messages(self, page: int = 0) -> list[dict[str, Any]]:
        """Read one page of SMS messages, newest first."""
        response = self.get(
            {
                "cmd": "sms_data_total",
                "page": page,
                "data_per_page": 100,
                "mem_store": 1,
                "tags": 10,
                "order_by": "order by id desc",
            }
        )
        messages = response.get("messages")
        if not isinstance(messages, list):
            raise RuntimeError("Router did not return an SMS inbox")
        return [
            {
                "id": str(item.get("id", "")),
                "number": str(item.get("number", "")),
                "date": str(item.get("date", "")),
                "text": decode_message(str(item.get("content", ""))),
            }
            for item in messages
            if isinstance(item, dict)
        ]

    def wait_for(self, command: int) -> None:
        """Wait for completion, distinguishing router acceptance from success."""
        for _ in range(30):
            result = str(
                self.get({"cmd": "sms_cmd_status_info", "sms_cmd": command}).get(
                    "sms_cmd_status_result", ""
                )
            )
            if result == "3":
                return
            if result == "2":
                raise RuntimeError("The router reported that the SMS operation failed")
            time.sleep(1)
        raise RuntimeError(
            "Router accepted the SMS operation but completion is unknown; check the router before retrying"
        )

    def delete(self, ids: list[str]) -> None:
        """Delete explicitly selected IDs after confirmation by the caller."""
        if not ids or any(not re.fullmatch(r"\d+", value) for value in ids):
            raise ValueError("Provide one or more numeric message IDs")
        result = self.set(
            {"goformId": "DELETE_SMS", "msg_id": ";".join(ids) + ";", "notCallback": "true"}
        )
        if result.get("result") != "success":
            raise RuntimeError("Router did not accept the delete request")
        self.wait_for(6)

    def send(self, number: str, message: str) -> None:
        """Send a message after confirmation by the caller."""
        if not re.fullmatch(r"\+?[0-9]{3,20}", number) or not message:
            raise ValueError("A phone number and non-empty message are required")
        if any(ord(c) > 0xFFFF for c in message):
            raise ValueError(
                "This router does not reliably encode characters outside the basic Unicode plane"
            )
        gsm = set(
            "\n\r\f !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_abcdefghijklmnopqrstuvwxyz{|}~\u00a0¡£¤¥§¿ÄÅÆÇÉÑÖØÜßàäåæèéìñòöøùüΓΔΘΛΞΠΣΦΨΩ€"
        )
        encode_type = "GSM7_default" if all(c in gsm for c in message) else "UNICODE"
        now = datetime.now().astimezone()
        offset = now.utcoffset()
        hours = (offset.total_seconds() / 3600) if offset else 0
        zone = f"{hours:+g}" if hours > 0 else f"{hours:g}"
        result = self.set(
            {
                "goformId": "SEND_SMS",
                "notCallback": "true",
                "Number": number,
                "sms_time": now.strftime("%y;%m;%d;%H;%M;%S;") + zone,
                "MessageBody": "".join(f"{ord(c):04X}" for c in message),
                "ID": -1,
                "encode_type": encode_type,
            }
        )
        if result.get("result") != "success":
            raise RuntimeError("Router did not accept the send request")
        self.wait_for(4)


def perform(request: dict[str, Any]) -> dict[str, Any]:
    """Run a validated router operation for the native frontend."""
    action = request.get("action")
    if action == "status":
        return {"configured": load_profile() is not None}
    if action == "setup":
        save_profile(
            str(request.get("url", "")),
            str(request.get("username", "")),
            str(request.get("password", "")),
        )
        return {"saved": True}
    profile = load_profile()
    if profile is None:
        raise ValueError("Set up the router first")
    try:
        password = _keyring().get_password(SERVICE, ACCOUNT)
    except Exception as error:
        raise RuntimeError(
            "Could not read the router password from the OS credential service"
        ) from error
    if not password:
        raise ValueError("Router password is missing from the OS credential store; run setup again")
    client = RouterClient(profile["url"])
    client.login(profile["username"], password)
    try:
        if action == "list":
            page = int(request.get("page", 0))
            if page < 0:
                raise ValueError("Page must be non-negative")
            return {"messages": client.messages(page)}
        if action == "send":
            client.send(str(request.get("number", "")), str(request.get("message", "")))
        elif action == "delete":
            ids = request.get("ids")
            if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
                raise ValueError("Message IDs must be a list")
            client.delete(ids)
        else:
            raise ValueError("Unknown router SMS action")
        return {"success": True}
    finally:
        # Releasing the web session avoids accumulating duplicate login sessions.
        try:
            client.set({"goformId": "LOGOUT"})
        except RuntimeError:
            pass
