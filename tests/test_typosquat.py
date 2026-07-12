import pytest
from CONFUSERAY.typosquat import _edit_distance, check_typosquat, find_typosquats


@pytest.mark.parametrize("str1,str2,expected", [
    ("abc", "abc", 0),           # identical
    ("abc", "abcd", 1),          # insert
    ("abcd", "abc", 1),          # delete
    ("abc", "axc", 1),           # replace
    ("", "abc", 3),              # empty
])
def test_edit_distance(str1, str2, expected):
    assert _edit_distance(str1, str2) == expected


@pytest.mark.parametrize("candidate,candidates,expected", [
    ("acme-atuh", ["acme-auth", "billing-core"], "acme-auth"),  # close match
    ("acme-auth", ["acme-auth"], None),                         # exact match (skip)
    ("completely-different", ["acme-auth"], None),              # no match
])
def test_check_typosquat(candidate, candidates, expected):
    assert check_typosquat(candidate, candidates) == expected


@pytest.mark.parametrize("deps,candidates,expected", [
    ([("acme-atuh", "1.0", "x"), ("react", "18.0", "y")], ["acme-auth"], {"acme-atuh": "acme-auth"}),
    ([], ["acme-auth"], {}),
])
def test_find_typosquats(deps, candidates, expected):
    assert find_typosquats(deps, candidates) == expected
