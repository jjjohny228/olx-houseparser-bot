import asyncio
import logging
import os

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters import Text
from aiogram.types import ParseMode
from bs4 import BeautifulSoup
import requests
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from datetime import datetime, timedelta
import pytz
from keyboards.client_keyboards import *
from create_bot import dp, bot
from data_base.data_functions import check_copy_apartment, get_city_name, change_city

HOST = os.getenv('HOST')


class CityGroup(StatesGroup):
    new_city = State()


# Флаг для контроля состояния поиска
search_active = False


# Обработчик команды /start
async def start_command(message: types.Message):
    print(HOST)
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
    city = await get_city_name(message.from_user.id)
    global search_active
    if search_active:
        await message.answer("Поиск уже выполняется")
        return

    await message.answer("Начинаю поиск объявлений...", reply_markup=get_cancel_keyboard())
    search_active = True

    # Запуск циклического поиска объявлений
    while search_active:
        try:
            kiev_timezone = pytz.timezone('Europe/Kiev')
            ads_found = await parse_olx_ads(city)  # Вызов функции парсинга объявлений
            for ad in ads_found:
                flet_id = await check_copy_apartment(ad['link'])
                print(flet_id)
                realtor = None
                if flet_id:
                    if flet_id % 2 != 0:
                        realtor = 'Глеб'
                    else:
                        realtor = 'Максим'
                    ad_text = f"**{ad['title']}**\nЦена: {ad['price']}\nВремя: {ad['time']}\nРиелтор: {realtor}\nЛокация: {ad['location']}"
                    await bot.send_photo(chat_id=message.from_user.id,
                                         photo=ad['photo_url'],
                                         caption=ad_text,
                                         parse_mode=ParseMode.MARKDOWN,
                                         reply_markup=get_url_keyboard(ad['link']))
                    await asyncio.sleep(1)
                else:
                    print('Уже в списке')
        except Exception as e:
            logging.exception(f"Ошибка при поиске объявлений: {e}")

        await asyncio.sleep(30)  # Ждем 1.5 секунды перед следующим поиском
    # Сброс флага при остановке поиска
    search_active = False


# Функция чтобы отменить изменение города
async def cancel_new_city(message: types.Message, state: FSMContext):
    await check_host(message)
    if state is None:
        await message.answer('Город остался прежним', reply_markup=get_menu_keyboard())
        return
    await state.finish()
    await message.answer('Город остался прежним', reply_markup=get_menu_keyboard())


# Обработчик команды /setcity
async def set_city_command(message: types.Message):
    await check_host(message)
    await message.answer(f"Введите новый город:", reply_markup=get_cancel_city_keyboard())
    await CityGroup.new_city.set()


# Функция чтобы поменять город поиска
async def set_new_city(message: types.Message, state: FSMContext):
    await check_host(message)
    await change_city(message.from_user.id, message.text)
    await state.finish()
    await message.answer('Город был успешно изменен', reply_markup=get_menu_keyboard())


# Функция парсинга объявлений OLX.ua
async def parse_olx_ads(city: str) -> list:
    ads = []
    # Определение киевской временной зоны
    kiev_timezone = pytz.timezone('Europe/Kiev')

    # Получение текущего времени в киевской временной зоне
    search_start_time = datetime.now(kiev_timezone)

    # Здесь выполняется парсинг объявлений на странице OLX.ua
    url = f'https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/' \
          f'?currency=UAH&search%5Bprivate_business%5D=private&search%5Border%5D=created_at:desc#808146671'
    print(url)
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'lxml')
    ad_items = soup.find_all('div', class_='css-1sw7q4x')

    for ad_item in ad_items[3:7]:
        try:
            location_text = ad_item.find('p', class_='css-veheph er34gjf0').text.strip()
            location = location_text[:location_text.find(',')]
            link = 'https://www.olx.ua' + ad_item.find('a', class_='css-rc5s2u').get('href')

            # Переходим по ссылке объявления
            ad_response = requests.get(link)
            ad_soup = BeautifulSoup(ad_response.content, 'lxml')

            # Высчитываем разницу во времени
            publish_time_element = ad_soup.find('span', class_='css-19yf5ek')
            publish_time_list = publish_time_element.text.strip().split()
            print(publish_time_list)
            if publish_time_list[0] != 'Сьогодні':
                continue

            publish_time = datetime.strptime(publish_time_list[-1], '%H:%M').time()
            search_time_margin = timedelta(minutes=210)
            search_start_time_margin = (
                    datetime.combine(datetime.today(), search_start_time.time()) - search_time_margin).time()

            # Находим интересующие нас данные
            title = ad_item.find('h6', class_='css-16v5mdi er34gjf0').text.strip()
            price = ad_item.find('p', class_='css-10b0gli er34gjf0').text.strip()
            # description = ad_soup.find('div', class_='css-bgzo2k er34gjf0').text.strip()
            photo_url = ad_soup.find('img', class_='css-1bmvjcs').get('src')

            # Проверяем чтобы время публикации отличалось от нашего не больше чем на 5 минут и заполняем словарь
            if publish_time >= search_start_time_margin:
                print('True')
                ads.append({
                    'title': title,
                    'price': price,
                    'link': link,
                    'photo_url': photo_url,
                    'time': publish_time_list[-1],
                    'location': location
                })
        except Exception as e:
            print(e)

    print(*ads, sep='\n')
    return ads


async def check_host(message):
    if message.from_user.id != int(HOST):
        await message.answer('Вы не владелец, доступ запрещен')
        return


def register_client_handlers(disp: Dispatcher):
    disp.register_message_handler(start_command, commands=['start'])
    disp.register_message_handler(stop_search_command, Text("Остановить"))
    disp.register_message_handler(search_ads_command, Text("Поиск🔎"))
    disp.register_message_handler(set_city_command, Text("Поменять город🔁"))
    disp.register_message_handler(cancel_new_city, Text("Не менять город🙅‍♂"), state='*')
    disp.register_message_handler(set_new_city, state=CityGroup.new_city)



