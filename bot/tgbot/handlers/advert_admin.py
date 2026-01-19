import json
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.types.inline_keyboard import InlineKeyboardButton, InlineKeyboardMarkup

from bot.tgbot.databases.pay_db import checkUserAdmin
from bot.tgbot.keyboards.inline import mainmenu_btn, mainmenubackbtn
from bot.tgbot.misc.states import AdvertAdminStates

from config import ADVERT_POSITIONS_FILE, logger_bot


def load_advert_positions():
    """Загружает позиции рекламы из файла"""
    try:
        with open(ADVERT_POSITIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("positions", [])
    except FileNotFoundError:
        # Если файл не найден, создаем с позициями по умолчанию
        default_positions = [
            {"key": "CIAN_city", "name": "ЦИАН (Екатеринбург и пригород)", "price": 364},
            {"key": "CIAN_country", "name": "ЦИАН (за пределом Свердловской области)", "price": 364},
            {"key": "AVITO_apartments", "name": "АВИТО квартиры", "price": 204},
            {"key": "AVITO_country_house", "name": "АВИТО загородка", "price": 1110},
            {"key": "AVITO_commercial", "name": "АВИТО коммерция", "price": 343},
            {"key": "AVITO_parkings", "name": "АВИТО паркинг", "price": 231},
            {"key": "AVITO_rent_apartments", "name": "АВИТО аренда квартир", "price": 196},
            {"key": "yandex_realty", "name": "ЯндексНедвижимость", "price": 66},
            {"key": "UPN", "name": "УПН", "price": 94},
            {"key": "DomClick", "name": "ДомКлик", "price": 165},
            {"key": "ULA", "name": "Юла", "price": 66},
        ]
        save_advert_positions(default_positions)
        return default_positions
    except Exception as e:
        logger_bot.error(f"Ошибка при загрузке позиций рекламы: {e}")
        return []


def save_advert_positions(positions):
    """Сохраняет позиции рекламы в файл"""
    try:
        data = {"positions": positions}
        with open(ADVERT_POSITIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger_bot.error(f"Ошибка при сохранении позиций рекламы: {e}")
        return False


def get_advert_admin_keyboard():
    """Создает клавиатуру для управления рекламой"""
    keyboard = InlineKeyboardMarkup(row_width=1)

    view_btn = InlineKeyboardButton(
        "📋 Посмотреть позиции", callback_data="advert_admin_view"
    )
    add_btn = InlineKeyboardButton(
        "➕ Добавить позицию", callback_data="advert_admin_add"
    )
    edit_btn = InlineKeyboardButton(
        "✏️ Редактировать позицию", callback_data="advert_admin_edit"
    )
    delete_btn = InlineKeyboardButton(
        "🗑 Удалить позицию", callback_data="advert_admin_delete"
    )

    keyboard.add(view_btn, add_btn, edit_btn, delete_btn)
    keyboard.row(mainmenubackbtn)

    return keyboard


async def advert_admin_start(cb: CallbackQuery, state: FSMContext):
    """Начало работы с управлением рекламой"""
    await state.finish()

    # Проверяем права администратора
    user_adm = checkUserAdmin(cb.from_user.id)
    if user_adm != "admin":
        await cb.message.edit_text("❌ У вас нет прав для доступа к этой функции.")
        return

    await cb.message.edit_text(
        "<b>🎯 Управление позициями рекламы</b>\n\n" "Выберите действие:",
        reply_markup=get_advert_admin_keyboard(),
    )


async def advert_admin_view(cb: CallbackQuery, state: FSMContext):
    """Просмотр всех позиций рекламы"""
    await state.finish()

    positions = load_advert_positions()

    text = "<b>📋 Текущие позиции рекламы:</b>\n\n"

    for i, pos in enumerate(positions, 1):
        text += f"{i}. <b>{pos['name']}:</b> {pos['price']} ₽\n"

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="advert_admin"))
    keyboard.row(mainmenu_btn)

    await cb.message.edit_text(text, reply_markup=keyboard)


async def advert_admin_add(cb: CallbackQuery, state: FSMContext):
    """Добавление новой позиции рекламы"""
    await state.finish()

    await cb.message.edit_text(
        "<b>➕ Добавление новой позиции</b>\n\n"
        "Введите название позиции (например: 'ЦИАН Москва'):",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Отмена", callback_data="advert_admin")
        ),
    )

    await state.set_state(AdvertAdminStates.adding_name.state)


async def advert_admin_adding_name(msg: Message, state: FSMContext):
    """Обработка ввода названия новой позиции"""
    position_name = msg.text.strip()

    if not position_name:
        await msg.answer("❌ Название не может быть пустым. Попробуйте еще раз:")
        return

    # Проверяем, что название не слишком длинное
    if len(position_name) > 100:
        await msg.answer("❌ Название слишком длинное (максимум 100 символов). Попробуйте еще раз:")
        return

    await state.update_data(new_position_name=position_name)

    await msg.answer(
        f"<b>➕ Добавление позиции: {position_name}</b>\n\n"
        "Введите цену в рублях (только число):",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Отмена", callback_data="advert_admin_add")
        ),
    )

    await state.set_state(AdvertAdminStates.adding_price.state)


async def advert_admin_adding_price(msg: Message, state: FSMContext):
    """Обработка ввода цены для новой позиции"""
    try:
        price = float(msg.text.strip())
        if price < 0:
            await msg.answer("❌ Цена не может быть отрицательной. Попробуйте еще раз:")
            return

        data = await state.get_data()
        position_name = data.get("new_position_name")

        if not position_name:
            await msg.answer("❌ Ошибка: название позиции не найдено. Попробуйте заново.")
            await state.finish()
            return

        # Генерируем уникальный ключ для позиции
        positions = load_advert_positions()
        existing_keys = [pos["key"] for pos in positions]
        
        # Создаем ключ на основе названия
        base_key = "".join(c.lower() for c in position_name if c.isalnum())[:20]
        key = base_key
        counter = 1
        while key in existing_keys:
            key = f"{base_key}_{counter}"
            counter += 1

        # Добавляем новую позицию
        new_position = {
            "key": key,
            "name": position_name,
            "price": price
        }
        
        positions.append(new_position)
        save_advert_positions(positions)

        await msg.answer(
            f"✅ Позиция <b>{position_name}</b> добавлена с ценой <b>{price} ₽</b>"
        )

        await state.finish()
        # Показываем главное меню управления рекламой
        await msg.answer(
            "<b>🎯 Управление позициями рекламы</b>\n\n" "Выберите действие:",
            reply_markup=get_advert_admin_keyboard(),
        )

    except ValueError:
        await msg.answer("❌ Введите корректное число для цены:")


async def advert_admin_edit(cb: CallbackQuery, state: FSMContext):
    """Редактирование позиций рекламы"""
    await state.finish()

    positions = load_advert_positions()

    if not positions:
        await cb.message.edit_text(
            "❌ Нет позиций для редактирования",
            reply_markup=get_advert_admin_keyboard(),
        )
        return

    keyboard = InlineKeyboardMarkup(row_width=1)
    for i, pos in enumerate(positions):
        keyboard.add(
            InlineKeyboardButton(
                f"{i+1}. {pos['name']} - {pos['price']} ₽",
                callback_data=f"advert_admin_edit_{i}",
            )
        )

    keyboard.row(InlineKeyboardButton("◀️ Назад", callback_data="advert_admin"))

    await cb.message.edit_text(
        "<b>✏️ Редактирование позиций</b>\n\n" "Выберите позицию для редактирования:",
        reply_markup=keyboard,
    )


async def advert_admin_edit_position(cb: CallbackQuery, state: FSMContext):
    """Обработка выбора позиции для редактирования"""
    try:
        position_index = int(cb.data.split("_")[-1])
        positions = load_advert_positions()

        if position_index < 0 or position_index >= len(positions):
            await cb.answer("❌ Неверная позиция")
            return

        position = positions[position_index]
        await state.update_data(editing_index=position_index)

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "📝 Изменить название", callback_data="advert_admin_edit_name"
            )
        )
        keyboard.add(
            InlineKeyboardButton(
                "💰 Изменить цену", callback_data="advert_admin_edit_price"
            )
        )
        keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="advert_admin_edit"))

        await cb.message.edit_text(
            f"<b>✏️ Редактирование позиции</b>\n\n"
            f"<b>Название:</b> {position['name']}\n"
            f"<b>Цена:</b> {position['price']} ₽\n\n"
            "Выберите что изменить:",
            reply_markup=keyboard,
        )

    except (ValueError, IndexError):
        await cb.answer("❌ Неверная позиция")


async def advert_admin_edit_name(cb: CallbackQuery, state: FSMContext):
    """Изменение названия позиции"""
    await cb.message.edit_text(
        "<b>📝 Изменение названия позиции</b>\n\n"
        "Введите новое название:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Отмена", callback_data="advert_admin_edit")
        ),
    )

    await state.set_state(AdvertAdminStates.editing_name.state)


async def advert_admin_edit_price(cb: CallbackQuery, state: FSMContext):
    """Изменение цены позиции"""
    await cb.message.edit_text(
        "<b>💰 Изменение цены позиции</b>\n\n"
        "Введите новую цену в рублях (только число):",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Отмена", callback_data="advert_admin_edit")
        ),
    )

    await state.set_state(AdvertAdminStates.editing_price.state)


async def advert_admin_editing_name(msg: Message, state: FSMContext):
    """Обработка ввода нового названия позиции"""
    new_name = msg.text.strip()

    if not new_name:
        await msg.answer("❌ Название не может быть пустым. Попробуйте еще раз:")
        return

    if len(new_name) > 100:
        await msg.answer("❌ Название слишком длинное (максимум 100 символов). Попробуйте еще раз:")
        return

    data = await state.get_data()
    position_index = data.get("editing_index")

    if position_index is None:
        await msg.answer("❌ Ошибка: позиция не найдена. Попробуйте заново.")
        await state.finish()
        return

    # Обновляем название позиции
    positions = load_advert_positions()
    if 0 <= position_index < len(positions):
        positions[position_index]["name"] = new_name
        save_advert_positions(positions)

        await msg.answer(f"✅ Название позиции изменено на <b>{new_name}</b>")

        await state.finish()
        # Показываем главное меню управления рекламой
        await msg.answer(
            "<b>🎯 Управление позициями рекламы</b>\n\n" "Выберите действие:",
            reply_markup=get_advert_admin_keyboard(),
        )
    else:
        await msg.answer("❌ Ошибка: позиция не найдена.")


async def advert_admin_editing_price(msg: Message, state: FSMContext):
    """Обработка ввода новой цены для позиции"""
    try:
        price = float(msg.text.strip())
        if price < 0:
            await msg.answer("❌ Цена не может быть отрицательной. Попробуйте еще раз:")
            return

        data = await state.get_data()
        position_index = data.get("editing_index")

        if position_index is None:
            await msg.answer("❌ Ошибка: позиция не найдена. Попробуйте заново.")
            await state.finish()
            return

        # Обновляем цену позиции
        positions = load_advert_positions()
        if 0 <= position_index < len(positions):
            old_price = positions[position_index]["price"]
            positions[position_index]["price"] = price
            save_advert_positions(positions)

            position_name = positions[position_index]["name"]
            await msg.answer(
                f"✅ Цена позиции <b>{position_name}</b> изменена с {old_price} ₽ на <b>{price} ₽</b>"
            )

            await state.finish()
            # Показываем главное меню управления рекламой
            await msg.answer(
                "<b>🎯 Управление позициями рекламы</b>\n\n" "Выберите действие:",
                reply_markup=get_advert_admin_keyboard(),
            )
        else:
            await msg.answer("❌ Ошибка: позиция не найдена.")

    except ValueError:
        await msg.answer("❌ Введите корректное число для цены:")


async def advert_admin_delete(cb: CallbackQuery, state: FSMContext):
    """Удаление позиций рекламы"""
    await state.finish()

    positions = load_advert_positions()

    if not positions:
        await cb.message.edit_text(
            "❌ Нет позиций для удаления", reply_markup=get_advert_admin_keyboard()
        )
        return

    keyboard = InlineKeyboardMarkup(row_width=1)
    for i, pos in enumerate(positions):
        keyboard.add(
            InlineKeyboardButton(
                f"{i+1}. {pos['name']} - {pos['price']} ₽",
                callback_data=f"advert_admin_delete_{i}",
            )
        )

    keyboard.row(InlineKeyboardButton("◀️ Назад", callback_data="advert_admin"))

    await cb.message.edit_text(
        "<b>🗑 Удаление позиций</b>\n\n" "Выберите позицию для удаления:",
        reply_markup=keyboard,
    )


async def advert_admin_delete_position(cb: CallbackQuery, state: FSMContext):
    """Обработка удаления позиции"""
    try:
        position_index = int(cb.data.split("_")[-1])
        positions = load_advert_positions()

        if position_index < 0 or position_index >= len(positions):
            await cb.answer("❌ Неверная позиция")
            return

        position = positions[position_index]

        # Подтверждение удаления
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "✅ Да, удалить",
                callback_data=f"advert_admin_confirm_delete_{position_index}",
            )
        )
        keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="advert_admin_delete"))

        await cb.message.edit_text(
            f"<b>🗑 Удаление позиции</b>\n\n"
            f'Вы уверены, что хотите удалить позицию <b>"{position["name"]}"</b>?',
            reply_markup=keyboard,
        )

    except (ValueError, IndexError):
        await cb.answer("❌ Неверная позиция")


async def advert_admin_confirm_delete(cb: CallbackQuery, state: FSMContext):
    """Подтверждение удаления позиции"""
    try:
        position_index = int(cb.data.split("_")[-1])
        positions = load_advert_positions()

        if position_index < 0 or position_index >= len(positions):
            await cb.answer("❌ Неверная позиция")
            return

        position = positions[position_index]

        # Удаляем позицию
        positions.pop(position_index)
        save_advert_positions(positions)

        await cb.message.edit_text(
            f'✅ Позиция <b>"{position["name"]}"</b> успешно удалена!',
            reply_markup=get_advert_admin_keyboard(),
        )

    except (ValueError, IndexError):
        await cb.answer("❌ Неверная позиция")


def register_advert_admin_handlers(dp: Dispatcher):
    """Регистрация обработчиков для управления рекламой"""

    # Основные обработчики
    dp.register_callback_query_handler(
        advert_admin_start,
        lambda c: c.data == "advert_admin",
        state=None,
    )

    dp.register_callback_query_handler(
        advert_admin_view,
        lambda c: c.data == "advert_admin_view",
        state=None,
    )

    dp.register_callback_query_handler(
        advert_admin_add,
        lambda c: c.data == "advert_admin_add",
        state=None,
    )

    dp.register_callback_query_handler(
        advert_admin_edit,
        lambda c: c.data == "advert_admin_edit",
        state=None,
    )

    dp.register_callback_query_handler(
        advert_admin_delete,
        lambda c: c.data == "advert_admin_delete",
        state=None,
    )

    # Обработчики для редактирования позиций
    dp.register_callback_query_handler(
        advert_admin_edit_position,
        lambda c: c.data.startswith("advert_admin_edit_") and c.data != "advert_admin_edit_name" and c.data != "advert_admin_edit_price",
        state=None,
    )

    dp.register_callback_query_handler(
        advert_admin_edit_name,
        lambda c: c.data == "advert_admin_edit_name",
        state=None,
    )

    dp.register_callback_query_handler(
        advert_admin_edit_price,
        lambda c: c.data == "advert_admin_edit_price",
        state=None,
    )

    # Обработчики для удаления позиций
    dp.register_callback_query_handler(
        advert_admin_delete_position,
        lambda c: c.data.startswith("advert_admin_delete_") and not c.data.startswith("advert_admin_confirm_delete_"),
        state=None,
    )

    dp.register_callback_query_handler(
        advert_admin_confirm_delete,
        lambda c: c.data.startswith("advert_admin_confirm_delete_"),
        state=None,
    )

    # Обработчики состояний
    dp.register_message_handler(
        advert_admin_adding_name,
        state=AdvertAdminStates.adding_name,
    )

    dp.register_message_handler(
        advert_admin_adding_price,
        state=AdvertAdminStates.adding_price,
    )

    dp.register_message_handler(
        advert_admin_editing_name,
        state=AdvertAdminStates.editing_name,
    )

    dp.register_message_handler(
        advert_admin_editing_price,
        state=AdvertAdminStates.editing_price,
    )