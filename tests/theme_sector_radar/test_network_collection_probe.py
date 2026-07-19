"""Prove the ordinary-suite deny-all policy is active during collection."""

import socket


try:
    socket.create_connection(("127.0.0.1", 9), timeout=0.01)
except RuntimeError as exc:
    _COLLECTION_NETWORK_BLOCKED = "network access is disabled" in str(exc)
except OSError:
    _COLLECTION_NETWORK_BLOCKED = False
else:
    _COLLECTION_NETWORK_BLOCKED = False


def test_network_is_blocked_before_test_fixtures_run():
    assert _COLLECTION_NETWORK_BLOCKED is True
