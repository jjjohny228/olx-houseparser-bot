import sqlite3 as sq


async def start_db():
    global db, cursor
    db = sq.connect('olx-houses.db')
    cursor = db.cursor()

    cursor.execute("CREATE TABLE IF NOT EXISTS apartment "
                   "(id INTEGER PRIMARY KEY AUTOINCREMENT, link TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS client_city "
                   "(id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER, city_name TEXT)")
    db.commit()


async def get_city_name(client_id):
    city = cursor.execute(f"SELECT city_name FROM client_city WHERE client_id = '{client_id}'").fetchone()
    if not city:
        cursor.execute(f"INSERT INTO client_city (client_id, city_name) VALUES({client_id}, 'dnepr')")
        db.commit()
        return 'dnepr'
    else:
        return city[0]


async def change_city(client_id, city_name):
    cursor.execute(f"UPDATE client_city SET city_name = '{city_name.lower()}' WHERE client_id = '{client_id}'")
    db.commit()


async def check_copy_apartment(apartment_link):
    check = cursor.execute(f"SELECT link "
                           f"FROM (SELECT link FROM  apartment ORDER BY id DESC LIMIT 5) q "
                           f"WHERE link = '{apartment_link}'").fetchone()
    if not check:
        cursor.execute(f"INSERT INTO apartment (link) VALUES('{apartment_link}')")
        flat_id = cursor.execute(f"SELECT id FROM apartment ORDER BY id DESC LIMIT 1").fetchone()
        db.commit()
        return flat_id[0]
    else:
        return False
