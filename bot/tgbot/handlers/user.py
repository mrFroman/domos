from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.tgbot.keyboards.inline import *
from bot.tgbot.databases.pay_db import *
from bot.tgbot.services.telegram_token_service import TelegramTokenService


async def user_start(message: Message, state: FSMContext):
    banned = getBannedUserId(message.from_user.id)
    if banned != 0:
        return

    username = message.from_user.username
    if username is None:
        await message.reply(
            "Для корректной работы необходимо изменить имя пользователя в настройках бота!"
        )
        return

    changeUsername(message.from_user.id, username)
    await state.finish()

    exists = checkUserExists(message.from_user.id)
    if exists == "empty":
        regUser(message.from_user.id, username)

    unique_code = message.text.split()[1] if len(message.text.split()) > 1 else None
    if unique_code and unique_code.startswith("telegram_"):
        if await TelegramTokenService.mark_token_processed(
            unique_code,
            message.from_user.id,
        ):
            # TODO На сервере должен быть урл с доменом
            # site_login_url = f"http://127.0.0.1:8002/auth/telegram/?token={unique_code}"
            site_login_url = f"https://neurochief.pro/domosclub/auth/telegram/?token={unique_code}"
            await message.reply(
                f'<a href="{site_login_url}">Войти на сайт через телеграм</a>',
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        else:
            await message.answer("Токен недействителен или истек!")
        return

    if unique_code:
        try:
            uniq_true = checkAdminLink(unique_code)
            if uniq_true == "successAdmined":
                changeUserAdminLink(message.from_user.id, 1, get_random_string(7))
            elif uniq_true == "404":
                try:
                    uniq_true = checkRefLink(unique_code, message.from_user.id)
                    if uniq_true == "successreferaled":
                        ref_uname = getUserById(unique_code)
                        sendLogToAdm(
                            f"Пользователь @{username} пришел в бота от @{ref_uname}"
                        )
                        sendLogToUser(
                            f"<i>По вашей ссылке в бота пришел @{username}!</i>",
                            unique_code,
                        )
                    elif uniq_true == "error404":
                        await message.answer("Такой ссылки не существует!")
                except:
                    pass
        except:
            pass

    await message.answer(
        "Вы в главном меню!", reply_markup=mainmenumk(message.from_user.id)
    )


async def main_menu(cb: CallbackQuery, state: FSMContext):
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
        changeUsername(cb.from_user.id, cb.from_user.username)
        await state.finish()
        username = cb.from_user.username
        if username == None:
            await cb.message.edit_text(
                """
    Для корректной работы необходимо в настройках изменить имя пользователя!
    Как это сделать:
    Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
    После изменения @username войдите в бот по ссылке еще раз и нажмите /start
    """
            )
        else:
            exists = checkUserExists(cb.from_user.id)
            if exists == "empty":
                regUser(cb.from_user.id, username)
            await cb.message.answer(
                "Вы в главном меню!", reply_markup=mainmenumk(cb.from_user.id)
            )


async def main_menuanswer(cb: CallbackQuery, state: FSMContext):
    changeUsername(cb.from_user.id, cb.from_user.username)
    banned = getBannedUserId(cb.from_user.id)
    if banned == 0:
        await state.finish()
        username = cb.from_user.username
        if username == None:
            await cb.message.answer(
                """
    Для корректной работы необходимо в настройках изменить имя пользователя!
    Как это сделать:
    Настройки - Изм. (Редактирование пользователя) - Имя пользователя.
    После изменения @username войдите в бот по ссылке еще раз и нажмите /start
    """
            )
        else:
            exists = checkUserExists(cb.from_user.id)
            if exists == "empty":
                regUser(cb.from_user.id, username)
            await cb.message.answer(
                "Вы в главном меню!", reply_markup=mainmenumk(cb.from_user.id)
            )


def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands=["start"], state="*")
    dp.register_callback_query_handler(
        main_menu, lambda c: c.data == "mainmenu", state="*"
    )
    dp.register_callback_query_handler(
        main_menuanswer, lambda c: c.data == "mainmenuanswer", state="*"
    )
