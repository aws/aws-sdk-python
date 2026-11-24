# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""DO NOT MERGE: deliberate failures to check how parallel runs report them."""

from collections.abc import Iterator

import pytest


@pytest.fixture
def broken_setup() -> None:
    raise RuntimeError("intentional setup error in polly")


@pytest.fixture
def broken_teardown() -> Iterator[None]:
    yield
    raise RuntimeError("intentional teardown error in polly")


@pytest.mark.parametrize("mode", ["sync", "async"])
def test_intentional_assertion_failure(mode: str) -> None:
    expected = {"client": "polly", "mode": mode, "value": 1}
    actual = {"client": "polly", "mode": mode, "value": 2}
    assert actual == expected


def test_intentional_exception() -> None:
    raise ValueError("intentional exception in polly")


def test_intentional_setup_error(broken_setup: None) -> None:
    pass


def test_intentional_teardown_error(broken_teardown: None) -> None:
    pass


def test_intentional_pass() -> None:
    assert True
