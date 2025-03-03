import json
from pydantic import BaseModel
import asyncpg
from fastapi import FastAPI
import random
from typing import Optional

app = FastAPI()

items_character = ["Урон", "Скорость Атаки", "Ловкость", "Интелект", "Сила", "Броня", "Шипы", "Сопротивление к огню",
                   "Сопротивление к льду", "Сопротивление к молнии", "Сопротивление к хаосу"]


class Search(BaseModel):
    characteristics: Optional[dict[str, int]] = None


async def get_db():
    conn = await asyncpg.connect('postgresql://nayont:t333444ob@localhost/SEREGAtrade')
    try:
        yield conn
    finally:
        await conn.close()


@app.get("/")
async def get_users():
    async for conn in get_db():
        rows = await conn.fetch("SELECT * FROM users")
        return rows


@app.put("/create_item")
async def create_item(name_item: str, how_much_characteristics: int, user_id: int):
    characteristic = {}
    list_characheristics = []

    items_char = ["Damage", "Attack speed", "Dexterity", "Intelligence", "strength", "Armor", "Thorns",
                  "Fire resistance", "Ice resistance", "Lightning resistance", "Chaos Resistance"]

    for i in range(how_much_characteristics):
        a = random.randint(0, len(items_char) - 1)
        list_characheristics.append(items_char[a])
        index_for_pop = items_char.index(items_char[a])
        items_char.pop(index_for_pop)

    for char in list_characheristics:
        characteristic[char] = random.randint(1, 1000)

    async for conn in get_db():
        await conn.execute('''
        INSERT INTO items(title,characteristic,user_id) VALUES($1,$2,$3)
    ''', name_item, json.dumps(characteristic), user_id)
        return f"Item {name_item} was created"


@app.post("/create_user")
async def create_user(nickname: str):
    async for conn in get_db():
        await conn.execute('''
        INSERT INTO users(nickname) VALUES($1)
    ''', nickname)


@app.put("/create_trade")
async def create_trade(id_item: int, price: float):
    async for conn in get_db():
        info_items_title = await conn.fetchrow('SELECT title FROM items WHERE id = $1', id_item)
        info_items_characteristics = await conn.fetchrow(
            'SELECT characteristic FROM items WHERE id = $1 AND on_trade = false', id_item)
        for_info_author = await conn.fetchrow('SELECT user_id FROM items WHERE id = $1 AND on_trade = false', id_item)
        info_author = await conn.fetchrow('SELECT nickname FROM users WHERE id = $1', *for_info_author)

        await conn.execute('''
        INSERT INTO TRADE(title,characteristic,price,author) VALUES($1,$2,$3,$4)''', *info_items_title,
                           *info_items_characteristics, float(price), *info_author)

        await conn.execute('''
            UPDATE items SET on_trade = True WHERE id = $1''', id_item)
        return "TRADE ACTIVATE"


@app.put("/create_trade_item")
async def create_trade_item(item_id: int):
    async for conn in get_db():
        await conn.execute('''UPDATE items SET on_trade = $1 WHERE id = $2''', True, item_id)
    return "Item ready to trade"


@app.put("/trade")
async def trade_item(who_buy_id: int, item_id: int):
    async for conn in get_db():
        item_on_trade = await conn.fetchrow("SELECT on_trade from items WHERE id = $1", item_id)
        if item_on_trade["on_trade"]:
            await conn.execute('''UPDATE items SET user_id = $1 WHERE id = $2''', who_buy_id, item_id)


async def find_item_characteristics(dict_char=None):
    async for conn in get_db():
        a = await conn.fetch('''SELECT * FROM items''')
        search_item_id = []
        for i in a:
            characteristics = json.loads(i["characteristic"])
            if all(char in characteristics for char in dict_char):
                if all(dict_char[char] <= characteristics[char] for char in dict_char):
                    search_item_id.append(i["id"])
        c = await conn.fetch('''SELECT * FROM items WHERE id = ANY($1::int[])''', search_item_id)
        return c


@app.post("/search")
async def search(search_user_id: int = None, search_title=None, characteristic1: Search = None):
    async for conn in get_db():
        items_one = await conn.fetch(
            '''SELECT * FROM items WHERE user_id = COALESCE($1,user_id) AND title = COALESCE($2,title) AND on_trade = True''',
            search_user_id, search_title)

        if characteristic1.characteristics:
            items_one = await conn.fetch(
                '''SELECT * FROM items WHERE user_id = COALESCE($1,user_id) AND title = COALESCE($2,title) AND on_trade = True''',
                search_user_id, search_title)

            items_two = await find_item_characteristics(characteristic1.characteristics)
            search_items = []
            for item in items_one:
                if item in items_two:
                    search_items.append(item)
        else:
            return items_one
        return search_items
