"""Secrets are resolved from a named environment override or the OS keyring."""

import sys
import types

import pytest

from r10n_backend.secrets import get_secret, set_secret


def test_named_process_environment_override(monkeypatch):
    monkeypatch.setenv("R10N_SMTP_MARKETING_WORK_PASSWORD", "session-only")

    assert get_secret("marketing-work") == "session-only"


def test_plaintext_keyring_backends_are_rejected(monkeypatch):
    fake = types.ModuleType("keyring")

    class PlaintextBackend:
        priority = 0

    fake.__dict__["get_keyring"] = lambda: PlaintextBackend()
    fake.__dict__["set_password"] = lambda *args: pytest.fail("plaintext backend must not be used")
    monkeypatch.setitem(sys.modules, "keyring", fake)
    monkeypatch.delenv("R10N_SMTP_WORK_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="secure operating system credential store"):
        set_secret("work", "never-save-this")
