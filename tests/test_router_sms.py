"""Exercise the ZLT S10 protocol without contacting a real router."""

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import pytest

from r10n_backend import router_sms


@pytest.fixture
def router():
    """Provide a local router simulator recording observed requests."""
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            data = self.rfile.read(int(self.headers["Content-Length"])).decode()
            fields = {k: v[0] for k, v in parse_qs(data, keep_blank_values=True).items()}
            requests.append((self.path, fields))
            if fields.get("cmd") == "get_token":
                result = {"get_token": "test-token"}
            elif fields.get("goformId") == "LOGIN":
                result = {"result": "0"}
            elif fields.get("cmd") == "sms_data_total":
                result = {
                    "messages": [
                        {"id": "7", "number": "+1234", "date": "today", "content": "004800690021"}
                    ]
                }
            elif fields.get("cmd") == "sms_cmd_status_info":
                result = {"sms_cmd_status_result": "3"}
            else:
                result = {"result": "success"}
            raw = json.dumps(result).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", requests
    server.shutdown()
    thread.join()
    server.server_close()


def test_list_send_delete_follow_s10_protocol(router):
    url, requests = router
    client = router_sms.RouterClient(url)
    client.login("admin", "password")
    assert client.messages() == [{"id": "7", "number": "+1234", "date": "today", "text": "Hi!"}]
    client.send("+1234567", "Hello!")
    client.delete(["7", "9"])
    forms = [entry[1] for entry in requests]
    assert forms[1]["CSRFToken"] == "test-token"
    assert forms[1]["username"] == base64.b64encode(b"admin").decode()
    assert forms[1]["password"] == base64.b64encode(b"5f4dcc3b5aa765d61d8327deb882cf99").decode()
    assert forms[2]["cmd"] == "sms_data_total"
    send = next(f for f in forms if f.get("goformId") == "SEND_SMS")
    assert send["MessageBody"] == "00480065006C006C006F0021"
    assert send["encode_type"] == "GSM7_default"
    delete = next(f for f in forms if f.get("goformId") == "DELETE_SMS")
    assert delete["msg_id"] == "7;9;"
    assert [f["sms_cmd"] for f in forms if f.get("cmd") == "sms_cmd_status_info"] == ["4", "6"]


def test_invalid_ids_cannot_trigger_delete(router):
    url, requests = router
    client = router_sms.RouterClient(url)
    with pytest.raises(ValueError):
        client.delete(["1;2"])
    assert requests == []


def test_profile_stores_only_nonsecret_values(tmp_path, monkeypatch):
    values = {}

    class Ring:
        def get_password(self, service, account):
            return values.get((service, account))

        def set_password(self, service, account, secret):
            values[service, account] = secret

    monkeypatch.setenv("R10N_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(router_sms, "_keyring", lambda: Ring())
    router_sms.save_profile("192.168.1.1", "admin", "private password")
    assert router_sms.load_profile() == {"url": "http://192.168.1.1", "username": "admin"}
    assert "private password" not in router_sms.profile_path().read_text()
    assert values[router_sms.SERVICE, router_sms.ACCOUNT] == "private password"


def test_unsupported_unicode_is_rejected_before_send(router):
    url, requests = router
    with pytest.raises(ValueError):
        router_sms.RouterClient(url).send("+123456", "😀")
    assert requests == []


def test_failed_router_send_does_not_report_success_or_poll(monkeypatch):
    client = router_sms.RouterClient("http://127.0.0.1")
    operations = []

    def reject(params):
        operations.append(params)
        return {"result": "failure"}

    monkeypatch.setattr(client, "set", reject)
    with pytest.raises(RuntimeError, match="did not accept"):
        client.send("+123456", "Hello")
    assert len(operations) == 1


def test_credential_failure_does_not_expose_password(tmp_path, monkeypatch):
    class Ring:
        def get_password(self, service, account):
            return None

        def set_password(self, service, account, secret):
            raise RuntimeError("secret=" + secret)

    monkeypatch.setenv("R10N_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(router_sms, "_keyring", lambda: Ring())
    with pytest.raises(RuntimeError) as error:
        router_sms.save_profile("192.168.1.1", "admin", "sensitive")
    assert "sensitive" not in str(error.value)
    assert not router_sms.profile_path().exists()
