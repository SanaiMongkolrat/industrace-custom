"""Unit tests for router-level RBAC section access."""
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.services.rbac import _resolve_min_level, require_section_access
from app.services.rbac_permissions import VIEWER_DEFAULT_PERMISSIONS, ADMIN_DEFAULT_PERMISSIONS


def test_resolve_min_level_get_is_read():
    assert _resolve_min_level("GET", "/sites") == 1


def test_resolve_min_level_post_is_write():
    assert _resolve_min_level("POST", "/sites") == 2


def test_resolve_min_level_delete_is_delete():
    assert _resolve_min_level("DELETE", "/sites/abc") == 3


def test_resolve_min_level_bulk_path_is_bulk():
    # P36 trap: any path containing 'bulk' escalates to level 4.
    # /assets/bulk-update and /assets/bulk-soft-delete were the 3rd P36
    # production incident; renamed to /multi-* (see Task 2 of plan 2026-09-04_163700).
    # Kept here as a regression guard so a future 'bulk-*' route is flagged.
    assert _resolve_min_level("POST", "/assets/bulk-update") == 4
    assert _resolve_min_level("POST", "/assets/bulk-soft-delete") == 4
    assert _resolve_min_level("POST", "/assets/anything/bulk") == 4


def test_resolve_min_level_renamed_multi_path_is_post():
    # After rename (P36 fix), /assets/multi-* paths do NOT match the
    # bulk keyword and resolve to standard POST level 2.
    # Admin holds level 3 on assets, so 200/422 is reachable for admin.
    assert _resolve_min_level("POST", "/assets/multi-update") == 2
    assert _resolve_min_level("POST", "/assets/multi-soft-delete") == 2


def test_resolve_min_level_import_preview_post_d02b78f():
    # d02b78f removed '/import/' from _BULK_PATH_KEYWORDS so the asset
    # CSV import endpoints are reachable at standard POST level 2.
    # (Previous test on this file asserted ==4; corrected 2026-09-04.)
    assert _resolve_min_level("POST", "/assets/import/xlsx/preview") == 2
    assert _resolve_min_level("POST", "/assets/import/xlsx") == 2


def _make_request(method: str, path: str) -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "query_string": b"",
    }
    return Request(scope)


class _Role:
    def __init__(self, permissions):
        self.permissions = permissions

    def get_effective_permissions(self):
        return self.permissions


class _User:
    def __init__(self, permissions):
        self.role = _Role(permissions)


def test_viewer_denied_write_on_sites():
    dependency = require_section_access("sites")
    user = _User(VIEWER_DEFAULT_PERMISSIONS)
    request = _make_request("POST", "/sites")

    with pytest.raises(HTTPException) as exc:
        dependency(request=request, current_user=user)
    assert exc.value.status_code == 403


def test_viewer_allowed_read_on_sites():
    dependency = require_section_access("sites")
    user = _User(VIEWER_DEFAULT_PERMISSIONS)
    request = _make_request("GET", "/sites")
    assert dependency(request=request, current_user=user) is True


def test_admin_allowed_delete_on_sites():
    dependency = require_section_access("sites")
    user = _User(ADMIN_DEFAULT_PERMISSIONS)
    request = _make_request("DELETE", "/sites/abc")
    assert dependency(request=request, current_user=user) is True


def test_skip_path_contains_bypasses_check():
    dependency = require_section_access("users", skip_path_contains=("/users/me",))
    user = _User(VIEWER_DEFAULT_PERMISSIONS)  # users: 0
    request = _make_request("GET", "/users/me")
    assert dependency(request=request, current_user=user) is True
