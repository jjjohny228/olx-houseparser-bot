import asyncio
import logging
import os

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text
from aiogram.types import ParseMode
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import pytz
from keyboards.client_keyboards import *
from create_bot import dp, bot
from data_base.data_functions import check_copy_apartment
from config import cities, city_chats

HOST = os.getenv('HOST')


# Флаг для контроля состояния поиска
search_active = False


# Обработчик команды /start
async def start_command(message: types.Message):
    await check_host(message)
    await message.reply("Привет! Я бот для поиска объявлений на OLX.ua. Для начала парсинга нажми  'Поиск🔎'",
                        reply_markup=get_menu_keyboard())


# Обработка команды 'Остановить'
async def stop_search_command(message: types.Message):
    await check_host(message)
    global search_active
    if search_active:
        search_active = False
        await message.answer("Поиск остановлен", reply_markup=get_menu_keyboard())
    else:
        await message.answer("Поиск не выполняется", reply_markup=get_menu_keyboard())


# Обработка команды 'Поиск🔎'
async def search_ads_command(message: types.Message):
    await check_host(message)
    global search_active
    if search_active:
        await message.answer("Поиск уже выполняется")
        return

    await message.answer("Начинаю поиск объявлений...", reply_markup=get_cancel_keyboard())
    search_active = True

    # Запуск циклического поиска объявлений
    while search_active:
        try:
            ads_found = await parse_olx_ads()  # Вызов функции парсинга объявлений
            for ad in ads_found:
                print(ad)
                check_flet_in_database = await check_copy_apartment(ad['link'])
                print(f"**{ad['title']}**\nЦена: {ad['price']}\nВремя: {ad['time']}\nЛокация: {ad['location']}")
                city_location = ad['location']
                print("ЛОкация город", city_location[:city_location.find(',')])
                print(city_location.find(','), "это номер запятой")

                if check_flet_in_database and city_location[:city_location.find(',')] in cities:
                    ad_text = f"**{ad['title']}**\nЦена: {ad['price']}\nВремя публикации: {ad['time']}\nЛокация: {ad['location']}"
                    await bot.send_photo(chat_id=city_chats[ad['location']],
                                         photo=ad['photo_url'],
                                         caption=ad_text,
                                         parse_mode=ParseMode.MARKDOWN,
                                         reply_markup=get_url_keyboard(ad['link']))
                    await asyncio.sleep(1)
                else:
                    print('Уже в списке')
        except Exception as e:
            logging.exception(f"Ошибка при поиске объявлений: {e}")

        await asyncio.sleep(5)  # Ждем 1.5 секунды перед следующим поиском
    # Сброс флага при остановке поиска
    search_active = False


# Функция парсинга объявлений OLX.ua
async def parse_olx_ads() -> list:
    ads = []
    # Определение киевской временной зоны
    kiev_timezone = pytz.timezone('Europe/Kiev')

    # Получение текущего времени в киевской временной зоне
    search_start_time = datetime.now(kiev_timezone)

    # Здесь выполняется парсинг объявлений на странице OLX.ua
    url = f'https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/' \
          f'?currency=UAH&search%5Bprivate_business%5D=private&search%5Border%5D=created_at:desc'
    response = requests.get(url)
    print(response.status_code)
    soup = BeautifulSoup(response.content, 'lxml')
    ad_items = soup.find_all('div', class_='css-1sw7q4x')

    for ad_item in ad_items[3:7]:
        try:
            location_text = ad_item.find('p', class_='css-veheph er34gjf0').text.strip()
            location = location_text[:location_text.find(' -')]
            link = 'https://www.olx.ua' + ad_item.find('a', class_='css-rc5s2u').get('href')

            # Переходим по ссылке объявления
            ad_response = requests.get(link)
            ad_soup = BeautifulSoup(ad_response.content, 'lxml')

            publish_time_element = ad_soup.find('span', class_='css-19yf5ek')
            publish_time_list = publish_time_element.text.strip().split()

            # Выяисление времени публикации
            publish_time = datetime.strptime(publish_time_list[-1], '%H:%M').time()
            datetime_publish_time = datetime.combine(datetime(1900, 1, 1), publish_time)
            new_time = datetime_publish_time + timedelta(hours=3)
            publish_time = new_time.time()

            # Находим интересующие нас данные
            title = ad_item.find('h6', class_='css-16v5mdi er34gjf0').text.strip()
            price = ad_item.find('p', class_='css-10b0gli er34gjf0').text.strip()
            photo_url = ad_soup.find('img', class_='css-1bmvjcs').get('src')

            ads.append({
                'title': title,
                'price': price,
                'link': link,
                'photo_url': photo_url,
                'time': publish_time,
                'location': location
            })
        except Exception as e:
            print("Была, ошибка", e.args)

    print(ads, sep='\n')
    return ads


async def check_host(message):
    if message.from_user.id != int(HOST):
        await message.answer('Вы не владелец, доступ запрещен')
        return


def register_client_handlers(disp: Dispatcher):
    disp.register_message_handler(start_command, commands=['start'])
    disp.register_message_handler(stop_search_command, Text("Остановить"))
    disp.register_message_handler(search_ads_command, Text("Поиск🔎"))



