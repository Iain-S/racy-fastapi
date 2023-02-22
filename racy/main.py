import asyncio
from typing import Union

import databases
import psycopg2
import uvicorn
from asyncpg.exceptions import LockNotAvailableError
from fastapi import FastAPI
from sqlalchemy.sql import text

app = FastAPI()

# Should match that in alembic.ini
CONNECTION_DSN = "postgresql://postgres:password@localhost/postgres"
database = databases.Database(CONNECTION_DSN)

# 4s is plenty of time to manually start two requests
SLEEP_FOR = 4

lock = asyncio.Lock()


@app.on_event("startup")
async def startup() -> None:
    await database.connect()


@app.on_event("shutdown")
async def shutdown() -> None:
    await database.disconnect()


@app.get("/")
async def read_root():
    """Demonstrate the issue we are trying to solve.

    Will run fine if called synchronously but will error if called concurrently.
    """
    results = await database.execute(text("select count(*) from test_table"))
    await asyncio.sleep(SLEEP_FOR)
    await database.execute(
        text("insert into test_table values ({}, {})".format(results + 1, 0))
    )
    return {"hello": str(results)}


@app.get("/show-table")
async def show_table():
    """Show all the rows in test_table."""
    results = [
        {**x} for x in await database.fetch_all(text("select * from test_table"))
    ]
    return results


@app.get("/nowait")
async def nowait():
    """Avoid race conditions with NOWAIT.

    This stops the race condition,
    but you need to handle the exception.
    """
    async with database.connection() as connection:
        async with connection.transaction():
            try:
                results = await database.fetch_all(
                    text("select id from test_table for update nowait")
                )

                # It's fine to SELECT ... NOWAIT more than once in the same transaction
                await database.fetch_all(
                    text("select id from test_table for update nowait")
                )

                await asyncio.sleep(SLEEP_FOR)
                max_id = max([x["id"] for x in results])
                await database.execute(
                    text("insert into test_table values ({}, {})".format(max_id + 1, 0))
                )
            except LockNotAvailableError:
                return "Table busy"

    return {"hello": str(max_id)}


@app.get("/for-update")
async def for_update():
    """Using FOR UPDATE does not stop the race condition."""
    async with database.connection() as connection:
        async with connection.transaction():
            results = await database.fetch_all(
                text("select id from test_table for update")
            )
            await asyncio.sleep(SLEEP_FOR)
            max_id = max([x["id"] for x in results])
            await database.execute(
                text("insert into test_table values ({}, {})".format(max_id + 1, 0))
            )

    return {"hello": str(max_id)}


@app.get("/table-lock")
async def table_lock():
    """Avoid race conditions with LOCK.

    This stops the race condition, but you need to be careful to avoid deadlock.
    """
    async with database.connection() as connection:
        async with connection.transaction():
            await database.execute(text("lock table test_table"))
            results = await database.execute(text("select count(*) from test_table"))
            await asyncio.sleep(SLEEP_FOR)
            await database.execute(
                text("insert into test_table values ({}, {})".format(results + 1, 0))
            )

    return {"hello": str(results)}


@app.get("/asyncio-lock")
async def asyncio_lock():
    """Avoid race conditions with asyncio.Lock.

    This stops the race condition, but only if there's a single uvicorn worker.
    """
    async with lock:
        results = await database.execute(text("select count(*) from test_table"))
        await asyncio.sleep(SLEEP_FOR)
        await database.execute(
            text("insert into test_table values ({}, {})".format(results + 1, 0))
        )

    return {"hello": str(results)}


@app.get("/sync")
def sync():
    """Avoid race conditions with a normal function.

    This stops the race condition, but only if there's a single uvicorn worker.
    """

    # Note that we need to use a synchronous db library
    conn = psycopg2.connect(CONNECTION_DSN)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM test_table")
    records = cur.fetchall()
    next_id = records[0][0] + 1
    cur.execute("INSERT INTO test_table VALUES (%s, 0)", (next_id,))

    return records


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
