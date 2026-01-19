import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()
path = str(Path(__file__).parents[0])

# --- Конфигурация ---
BOT_ADDITIONAL_TOKEN = os.getenv("BOT_ADDITIONAL_TOKEN")
ADMIN_IDS = os.getenv("ADMINS", []).split(
    ","
)  # Замените на реальные Telegram ID администраторов
GOOGLE_CREDENTIALS_FILE = f"{path}/service_account.json"
SPREADSHEET_NAME = "https://docs.google.com/spreadsheets/d/1k59CdZ0vdCcJnZMdXczKoQe2ExD26_wIHSm7lWxPRn0/edit?hl=ru&gid=473182526#gid=473182526"

# --- Настройка Google Sheets ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scope)
gs_client = gspread.authorize(creds)
spreadsheet = gs_client.open_by_url(SPREADSHEET_NAME)
sheet_training = spreadsheet.worksheet("Обучение")
sheet_openday = spreadsheet.worksheet("День открытых дверей")

# --- Настройка бота ---
storage = MemoryStorage()
bot = Bot(token=BOT_ADDITIONAL_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=storage)


# --- Состояния ---
class FormTraining(StatesGroup):
    full_name = State()
    phone = State()
    experience = State()
    current_income = State()
    desired_income = State()
    specialization = State()
    source = State()


class FormOpenDay(StatesGroup):
    full_name = State()
    phone = State()
    uznal = State()


# --- Клавиатура стартовая ---
start_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📝 Оставить заявку на обучение"),
            KeyboardButton(text="📅 Записаться на День открытых дверей ДомосКлаб"),
        ]
    ],
    resize_keyboard=True,
)


# --- Старт ---
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Добро пожаловать в ДомосКлаб! Выберите действие:", reply_markup=start_kb
    )


# --- Обучение ---
@dp.message(lambda message: message.text == "📝 Оставить заявку на обучение")
async def training_start(message: types.Message, state: FSMContext):
    await state.set_state(FormTraining.full_name)
    await message.answer("Введите ФИО:")


@dp.message(FormTraining.full_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(FormTraining.phone)
    await message.answer("Введите номер телефона:")


@dp.message(FormTraining.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(FormTraining.experience)
    await message.answer("Опыт в профессии Риелтор (в годах):")


@dp.message(FormTraining.experience)
async def process_experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await state.set_state(FormTraining.current_income)
    await message.answer("Текущий среднемесячный доход:")


@dp.message(FormTraining.current_income)
async def process_current_income(message: types.Message, state: FSMContext):
    await state.update_data(current_income=message.text)
    await state.set_state(FormTraining.desired_income)
    await message.answer("Желаемый среднемесячный доход:")


@dp.message(FormTraining.desired_income)
async def process_desired_income(message: types.Message, state: FSMContext):
    await state.update_data(desired_income=message.text)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Вторичная")],
            [KeyboardButton(text="Новостройки")],
            [KeyboardButton(text="Загородная")],
            [KeyboardButton(text="Коммерческая")],
            [KeyboardButton(text="Аренда")],
            [KeyboardButton(text="Другое")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    await state.set_state(FormTraining.specialization)
    await message.answer(
        "Выберите специализацию: (можно ввести вручную)", reply_markup=kb
    )


@dp.message(FormTraining.specialization)
async def process_specialization(message: types.Message, state: FSMContext):
    await state.update_data(specialization=message.text)
    await state.set_state(FormTraining.source)
    await message.answer(
        "Откуда узнали про проект?", reply_markup=types.ReplyKeyboardRemove()
    )


@dp.message(FormTraining.source)
async def process_source(message: types.Message, state: FSMContext):
    await state.update_data(source=message.text)
    data = await state.get_data()

    training_info = """
<b>🎉 Спасибо за ваши ответы.</b>

<b>📅 Информация по обучению:</b>
начало 07.07.25 
финиш 28.09.25

<b>💰 Стоимость участия:</b> 
для резидентов ДомосКлаб 20000 руб., 
для не резидентов 30000 руб. и 10% от каждой сделки проведённой в период действия кафедры (для всех категорий студентов)

Программа обучения предоставляется заранее.

🔥 Реальные истории успеха
https://disk.yandex.ru/d/v5vIJMmvFJDzKw
Наши выпускники уже увеличили доходы в 2-5 раз!

В ближайшее время мы с вами свяжемся!
    """
    await message.answer(training_info, reply_markup=start_kb)

    text = "<b>Новая заявка на обучение:</b>\n" + "\n".join(
        [
            f"ФИО: {data['full_name']}",
            f"Телефон: {data['phone']}",
            f"Опыт: {data['experience']}",
            f"Текущий доход: {data['current_income']}",
            f"Желаемый доход: {data['desired_income']}",
            f"Специализация: {data['specialization']}",
            f"Источник: {data['source']}",
        ]
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            print(f"Ошибка при отправке сообщения админу: {e}")

    sheet_training.append_row([datetime.now().isoformat()] + list(data.values()))
    await state.clear()


# --- День открытых дверей ---
@dp.message(
    lambda message: message.text == "📅 Записаться на День открытых дверей ДомосКлаб"
)
async def openday_start(message: types.Message, state: FSMContext):
    await state.set_state(FormOpenDay.full_name)
    await message.answer("Введите ФИО:")


@dp.message(FormOpenDay.full_name)
async def openday_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(FormOpenDay.phone)
    await message.answer("Введите номер телефона:")


@dp.message(FormOpenDay.phone)
async def openday_name(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(FormOpenDay.uznal)
    await message.answer("Откуда узнали про нас?")


@dp.message(FormOpenDay.uznal)
async def openday_phone(message: types.Message, state: FSMContext):
    await state.update_data(uznal=message.text)
    data = await state.get_data()

    await message.answer(
        "Спасибо за предоставленную информацию! Мы обязательно свяжемся с вами в ближайшее время.\n"
        # "День открытых дверей проходит ежемесячно, в предпоследнюю среду месяца.\n"
        "🕑 Время встречи: 22 января 2026 в 13:00\n"
        "📍 Место встречи:\nОфис ДомосКлаб\nОфисный дом «Суворов», ул. Радищева 6а, 1 подъезд, 10 этаж, офис 1006",
        reply_markup=start_kb,
    )

    text = f"<b>Запись на День открытых дверей:</b>\nФИО: {data['full_name']}\nТелефон: {data['phone']}\nУзнали о нас: {data['uznal']}"
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            print(f"Ошибка при отправке сообщения админу: {e}")

    sheet_openday.append_row(
        [datetime.now().isoformat(), data["full_name"], data["phone"], data["uznal"]]
    )
    await state.clear()


# --- Запуск ---
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
