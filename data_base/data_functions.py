import sqlite3 as sq


async def start_db():
    global db, cursor
    db = sq.connect('olx-houses.db')
    cursor = db.cursor()

    cursor.execute("CREATE TABLE IF NOT EXISTS apartment "
                   "(id INTEGER PRIMARY KEY AUTOINCREMENT, link TEXT)")
    db.commit()


async def check_copy_apartment(apartment_link):
    check = cursor.execute(f"SELECT link "
                           f"FROM (SELECT link FROM  apartment ORDER BY id DESC LIMIT 5) q "
                           f"WHERE link = '{apartment_link}'").fetchone()
    if not check:
        cursor.execute(f"INSERT INTO apartment (link) VALUES('{apartment_link}')")
        db.commit()
        return True
    else:
        return False
