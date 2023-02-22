import asyncio
from typing import Union

import databases
import uvicorn
from asyncpg.exceptions import LockNotAvailableError
from fastapi import FastAPI
from sqlalchemy.sql import text

app = FastAPI()

# Should match that in alembic.ini
database = databases.Database("postgresql://postgres:password@localhost/postgres")


@app.on_event("startup")
async def startup() -> None:
    await database.connect()


@app.get("/")
async def read_root():
    """Demonstrate the issue we are trying to solve.

    Will run fine if called synchronously but will error if called concurrently.
    """
    results = await database.execute(text("select count(*) from test_table"))
    await asyncio.sleep(5)
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

                await asyncio.sleep(3)
                max_id = max([x["id"] for x in results])
                await database.execute(
                    text("insert into test_table values ({}, {})".format(max_id + 1, 0))
                )
            except LockNotAvailableError:
                return "Table busy"

    return {"hello": str(max_id)}


@app.get("/with-for-update")
async def with_for_update():
    """Using FOR UPDATE does not stop the race condition."""
    async with database.connection() as connection:
        async with connection.transaction():
            results = await database.fetch_all(
                text("select id from test_table for update")
            )
            await asyncio.sleep(3)
            max_id = max([x["id"] for x in results])
            await database.execute(
                text("insert into test_table values ({}, {})".format(max_id + 1, 0))
            )

    return {"hello": str(max_id)}


@app.get("/explicit-lock")
async def explicit_lock():
    """Avoid race conditions with LOCK.

    This stops the race condition, but you need to be careful to avoid deadlock.
    """
    async with database.connection() as connection:
        async with connection.transaction():
            await database.execute(text("lock table test_table"))
            results = await database.execute(text("select count(*) from test_table"))
            await asyncio.sleep(3)
            await database.execute(
                text("insert into test_table values ({}, {})".format(results + 1, 0))
            )

    return {"hello": str(results)}


@app.get("/sync")
def sync():
    """Using a normal function does ..."""
    # ToDo Can we use psycopg directly here?
    raise NotImplementedError()


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
