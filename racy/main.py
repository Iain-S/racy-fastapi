from typing import Union

import asyncio
import databases
import uvicorn
from fastapi import FastAPI
from sqlalchemy.sql import text

app = FastAPI()

database = databases.Database("postgresql://postgres:password@localhost/postgres")


@app.on_event("startup")
async def startup() -> None:
    await database.connect()


@app.get("/")
async def read_root():
    results = await database.execute(text("select count(*) from test_table"))
    # results = [{**x} for x in await database.fetch_all(text("select * from test_table"))]
    await asyncio.sleep(5)
    await database.execute(text("insert into test_table values ({}, {})".format(results+1, 0)))
    
    return {"hello": str(results)}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

