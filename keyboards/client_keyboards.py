from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup


def get_url_keyboard(url):
    keyboard = InlineKeyboardMarkup(row_width=1)
    btn1 = InlineKeyboardButton(text='Обьявление🏠', url=url)
    keyboard.add(btn1)
    return keyboard


def get_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = KeyboardButton('Поиск🔎')
    btn2 = KeyboardButton('Поменять город🔁')
    keyboard.add(btn1).add(btn2)
    return keyboard


def get_cancel_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = KeyboardButton('Остановить')
    keyboard.add(btn1)
    return keyboard


def get_cancel_city_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = KeyboardButton("Не менять город🙅‍♂")
    keyboard.add(btn1)
    return keyboard

