import pytest


@pytest.skip
def test_q_validators_matches_validator(fuzzy_find):
    items = ["validator", "field", "config"]
    initial_search = "validators"
    found = fuzzy_find(items, initial_search)
    assert found == "validator"
