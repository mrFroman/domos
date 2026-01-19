from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def generation_options_keyboard(image_path: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔁 Сгенерировать заново",
                    callback_data=f"regenerate:{image_path}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="➕ Загрузить другое", callback_data="upload_new"
                )
            ],
        ]
    )
