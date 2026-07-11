import pytest
from CONFUSERAY.typosquat import _edit_distance, check_typosquat, find_typosquats


def test_edit_distance_identical():
    assert _edit_distance("abc", "abc") == 0


def test_edit_distance_one_insert():
    assert _edit_distance("abc", "abcd") == 1


def test_edit_distance_one_delete():
    assert _edit_distance("abcd", "abc") == 1


def test_edit_distance_one_replace():
    assert _edit_distance("abc", "axc") == 1


def test_edit_distance_empty():
    assert _edit_distance("", "abc") == 3


def test_check_typosquat_close_match():
    result = check_typosquat("acme-atuh", ["acme-auth", "billing-core"])
    assert result == "acme-auth"


def test_check_typosquat_exact_skip():
    result = check_typosquat("acme-auth", ["acme-auth"])
    assert result is None


def test_check_typosquat_no_match():
    result = check_typosquat("completely-different", ["acme-auth"])
    assert result is None


def test_find_typosquats_batch():
    deps = [
        ("acme-atuh", "1.0", "x"),
        ("react", "18.0", "y"),
    ]
    result = find_typosquats(deps, ["acme-auth"])
    assert result == {"acme-atuh": "acme-auth"}


def test_find_typosquats_empty():
    result = find_typosquats([], ["acme-auth"])
    assert result == {}
