from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def contact_lawyer_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("✍️ Написать текст", callback_data="text_vibot")],
            [InlineKeyboardButton("🎤 Записать голосовое", callback_data="golos")]
        ]
    )

def urgency_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("СРОЧНО (1 день)", callback_data="urgency_urgent")],
            [InlineKeyboardButton("Обычный (2 дня)", callback_data="urgency_normal")],
            [InlineKeyboardButton("Сложный (3 дня)", callback_data="urgency_complex")]
        ]
    )