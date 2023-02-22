from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from asyncpg import UniqueViolationError
from fastapi.testclient import TestClient

from racy.main import app


@pytest.fixture()
def client():
    # context manager will invoke startup event
    with TestClient(app) as client:
        with patch("racy.main.SLEEP_FOR", 1):
            yield client


def test_read_root(client) -> None:
    futures = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        for _ in range(2):
            futures.append(executor.submit(client.get, "/"))
        with pytest.raises(UniqueViolationError):
            for future in futures:
                future.result()


def test_nowait(client) -> None:
    futures = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        for _ in range(2):
            futures.append(executor.submit(client.get, "/nowait"))
        for future in futures:
            future.result()


def test_for_update(client) -> None:
    futures = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        for _ in range(2):
            futures.append(executor.submit(client.get, "/for-update"))
        with pytest.raises(UniqueViolationError):
            for future in futures:
                future.result()


def test_table_lock(client) -> None:
    futures = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        for _ in range(2):
            futures.append(executor.submit(client.get, "/table-lock"))
        for future in futures:
            future.result()


def test_asyncio_lock(client) -> None:
    futures = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        for _ in range(2):
            futures.append(executor.submit(client.get, "/asyncio-lock"))
        for future in futures:
            future.result()


def test_sync(client) -> None:
    futures = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        for _ in range(2):
            futures.append(executor.submit(client.get, "/sync"))
        for future in futures:
            future.result()
