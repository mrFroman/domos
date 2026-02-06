import string
import random
import datetime

from aiogram.types.inline_keyboard import *
from aiogram.utils.callback_data import CallbackData

from bot.tgbot.databases.pay_db import *


def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = "".join(random.choice(letters) for i in range(length))
    return result_str


firstfloor_btn = InlineKeyboardButton("10 этаж", callback_data="floornum_1")
# secondfloor_btn = InlineKeyboardButton('8 этаж', callback_data='floornum_2')

floornummk = InlineKeyboardMarkup().row(firstfloor_btn)

firstroom_btn = InlineKeyboardButton("Переговорная №1", callback_data="roomnum_1")
secroom_btn = InlineKeyboardButton("Переговорная №2", callback_data="roomnum_2")
thirdroom_btn = InlineKeyboardButton("Переговорная №1", callback_data="roomnum_3")
fourroom_btn = InlineKeyboardButton("Переговорная №2", callback_data="roomnum_4")
return_to_choice_floor_btn = InlineKeyboardButton(
    "◀️ Назад", callback_data="rent_meetingoffice"
)

firstfloor_roomnummk = (
    InlineKeyboardMarkup()
    .row(firstroom_btn)
    .row(secroom_btn)
    .row(return_to_choice_floor_btn)
)
secondfloor_roomnummk = (
    InlineKeyboardMarkup()
    .row(thirdroom_btn)
    .row(fourroom_btn)
    .row(return_to_choice_floor_btn)
)

mainmenu_btn = InlineKeyboardButton("◀️ В главное меню", callback_data="mainmenu")
mainmenu_mk = InlineKeyboardMarkup().add(mainmenu_btn)

mainmenuanswer_btn = InlineKeyboardButton(
    "◀️ В главное меню", callback_data="mainmenuanswer"
)
mainmenuanswer_mk = InlineKeyboardMarkup().add(mainmenuanswer_btn)

mainmenubackbtn = InlineKeyboardButton("◀️ Назад", callback_data="mainmenu")
mainmenubackbtnmk = InlineKeyboardMarkup(row_width=1).add(mainmenubackbtn)
helpfulbackbtn = InlineKeyboardButton("◀️ Назад", callback_data="Helpful")
helpfulbackbtnmk = InlineKeyboardMarkup(row_width=1).add(helpfulbackbtn)
helpfuldocbackbtn = InlineKeyboardButton("◀️ Назад", callback_data="Helpfuldoc")
helpfuldocbackbtnmk = InlineKeyboardMarkup(row_width=1).add(helpfulbackbtn)
firstdaybackbtn = InlineKeyboardButton("◀️ Назад", callback_data="fst_day")
firstdaybackbtnmk = InlineKeyboardMarkup(row_width=1).add(firstdaybackbtn)
ourrulesbackbtn = InlineKeyboardButton("◀️ Назад", callback_data="our_rules")
ourrulesbackbtnmk = InlineKeyboardMarkup(row_width=1).add(ourrulesbackbtn)
rieltorsbacanswerkbtn = InlineKeyboardButton(
    "◀️ Назад", callback_data="helpfulrieltorslistanswer"
)
rieltorsbackanswerbtnmk = InlineKeyboardMarkup(row_width=1).add(rieltorsbacanswerkbtn)

rieltorsbackbtn = InlineKeyboardButton("◀️ Назад", callback_data="helpfulrieltorslist")
rieltorsbackbtnmk = InlineKeyboardMarkup(row_width=1).add(rieltorsbacanswerkbtn)

contactsbackbtn = InlineKeyboardButton("◀️ Назад", callback_data="contacntshelpful")
contactsbackbtnmk = InlineKeyboardMarkup(row_width=1).add(contactsbackbtn)
contactsbacanswerkbtn = InlineKeyboardButton(
    "◀️ Назад", callback_data="contacntshelpfulanswer"
)
contactsbacanswerbtnmk = InlineKeyboardMarkup(row_width=1).add(contactsbacanswerkbtn)


def GenRieltorShowMK(user_id, rielt_id):
    rieltors_show_mk = InlineKeyboardMarkup(row_width=1)
    delrieltbtn = InlineKeyboardButton(
        "🎯 Удалить риэлтора", callback_data=f"delrietl_{rielt_id}"
    )
    useradm = checkUserAdmin(user_id)
    if useradm == "admin":
        rieltors_show_mk.add(delrieltbtn)
    rieltors_show_mk.add(rieltorsbacanswerkbtn)
    return rieltors_show_mk


def GenEventShowMK(user_id, event_id):
    mk = InlineKeyboardMarkup(row_width=1)
    delrieltbtn = InlineKeyboardButton(
        "🎯 Удалить событие", callback_data=f"delevent_{event_id}"
    )
    useradm = checkUserAdmin(user_id)
    if useradm == "admin":
        mk.add(delrieltbtn)
    mk.add(mainmenuanswer_btn)
    return mk


def GenContactShowMK(user_id, contact_id):
    rieltors_show_mk = InlineKeyboardMarkup(row_width=1)
    delrieltbtn = InlineKeyboardButton(
        "🎯 Удалить контакт", callback_data=f"delcont_{contact_id}"
    )
    useradm = checkUserAdmin(user_id)
    if useradm == "admin":
        rieltors_show_mk.add(delrieltbtn)
    rieltors_show_mk.add(contactsbacanswerkbtn)
    return rieltors_show_mk


# MAIN MENU
def mainmenumk(user_id):
    start_mk = InlineKeyboardMarkup(row_width=2)
    fst_day = InlineKeyboardButton("ℹ️ Первый день в компании", callback_data="fst_day")
    rent_meet = InlineKeyboardButton(
        "⌚️ Переговорка", callback_data="rent_meetingoffice"
    )
    checkrent_meet = InlineKeyboardButton(
        "🗓 Занятось переговорной", callback_data="check_meetingoffice"
    )

    our_rules = InlineKeyboardButton("🎯 Наши правила", callback_data="our_rules")
    feedback = InlineKeyboardButton("☎️ Обратная связь", callback_data="feedback")
    helpful = InlineKeyboardButton("📗 Полезное", callback_data="Helpful")
    eventsbtn = InlineKeyboardButton("🎊 Мероприятия", callback_data="eventsmenu")
    inviteref = InlineKeyboardButton(
        "📲 Пригласить друга", callback_data="invite_friend"
    )
    advertbtn = InlineKeyboardButton(
        "📮 Реклама", url="https://forms.gle/2czVRy78XsSDY1X16"
    )
    advertisementbtn = InlineKeyboardButton(
        "📮 Заявка на рекламу", callback_data="advertisement"
    )
    paysub = InlineKeyboardButton("💳 Оплата", callback_data="pay_invoice")
    subs_advantages = InlineKeyboardButton(
        "⭐️ Что входит в подписку", callback_data="sub_advantages"
    )

    support_chat = InlineKeyboardButton("💬 Техподдержка", callback_data="support_chat")
    # analysis = InlineKeyboardButton('⚖️ Аналитика', callback_data='analysis')
    settings = InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
    contract = InlineKeyboardButton(
        "ℹ️ Сформировать договор", callback_data="create_contract"
    )
    request_for_lawyer = InlineKeyboardButton(
        "📋 Заявка юристу на документ", callback_data="request_for_lawyer"
    )
    request_from_db = InlineKeyboardButton(
        "Найти информацию с помощью нейро-помощника",
        callback_data="start_request_from_db_process",
    )
    # start_mk.row(fst_day)
    start_mk.row(our_rules)
    # start_mk.row(request_for_lawyer)
    # start_mk.row(contract)
    start_mk.row(paysub, advertisementbtn)
    start_mk.row(helpful, rent_meet)
    start_mk.row(subs_advantages)
    start_mk.row(eventsbtn)
    start_mk.row(inviteref)
    start_mk.row(support_chat)
    adm = checkUserAdmin(user_id)
    if adm == "admin":
        start_mk.add(settings)
    return start_mk


def request_from_db_keyboard():
    keyboard = InlineKeyboardMarkup()
    request_floor_from_db = InlineKeyboardButton(
        "Подобрать квартиры", callback_data="start_request_floor_process"
    )
    request_info_from_db = InlineKeyboardButton(
        "Найти информацию из лекций", callback_data="start_request_info_process"
    )
    keyboard.row(request_floor_from_db)
    keyboard.row(request_info_from_db)
    keyboard.row(mainmenu_btn)
    return keyboard


def menu_blank_gpt(num):
    menu_blank = InlineKeyboardMarkup(row_width=2)

    edit_doc = InlineKeyboardButton(
        "заполнить документ", callback_data=f"edit_doc_{num}"
    )
    blank = InlineKeyboardButton("получить бланк", callback_data=f"helpfulblank{num}_1")

    menu_blank.row(edit_doc)
    menu_blank.row(blank)
    menu_blank.row(helpfulbackbtn)
    return menu_blank


def adminMenu():
    mk = InlineKeyboardMarkup(row_width=2)
    analysis = InlineKeyboardButton("⚖️ Аналитика", callback_data="analysis")
    makeadvert = InlineKeyboardButton("📢 Сделать рассылку", callback_data="makeadvert")
    searchuser = InlineKeyboardButton(
        "🔎 Найти пользователя", callback_data="searchuser"
    )
    getUnpaidExcel = InlineKeyboardButton(
        "🆓 Неоплаченные", callback_data="getUnpaidsInline"
    )
    getpaidExcel = InlineKeyboardButton("🟢 Оплаченные", callback_data="getpaidsInline")
    lawyerExcel = InlineKeyboardButton(
        "⚖️Запросы к юристу", callback_data="lawyer_inline"
    )
    advertExcel = InlineKeyboardButton(
        "📞Запросы на рекламные объявления", callback_data="advert_inline"
    )
    advert_new = InlineKeyboardButton(
        "📞Запросы к рекламе", callback_data="advert_inline_new"
    )
    addrieltor = InlineKeyboardButton(
        "➕ Добавить риэлтора", callback_data="addRieltorAdmin"
    )
    addcontact = InlineKeyboardButton(
        "➕ Добавить Контакт", callback_data="addContactAdmin"
    )
    google_sheet_btn = InlineKeyboardButton(
        text="📊 таблица обратной связи",
        # Замените на реальную ссылку
        url="https://docs.google.com/spreadsheets/d/17_deblA-6h1tWD4FHoo0n7DNrt44UA6j36daYj0Nl64/edit?usp=sharing",
    )
    advert_admin_btn = InlineKeyboardButton(
        "🎯 Управление рекламой", callback_data="advert_admin"
    )
    subs_advantages = InlineKeyboardButton(
        "⭐️ Что входит в подписку", callback_data="sub_advantages"
    )
    mk.add(
        analysis,
        makeadvert,
        searchuser,
        getUnpaidExcel,
        getpaidExcel,
        lawyerExcel,
        advertExcel,
    ),
    mk.row(advert_new)
    mk.row(advert_admin_btn)
    mk.row(subs_advantages)
    mk.row(google_sheet_btn)
    mk.row(addrieltor)
    mk.row(addcontact)
    mk.row(mainmenubackbtn)
    return mk


def genAnalysisMk():
    mk = InlineKeyboardMarkup(row_width=1)
    paid_users = getPaidUsers()
    for i in paid_users:
        mk.add(InlineKeyboardButton(f"@{i[0]}", callback_data="emptydata"))
    mk.row(mainmenu_btn)
    return mk


def genEventsMk(user_id):
    mk = InlineKeyboardMarkup(row_width=1)
    events = getEvents()
    now = datetime.datetime.now().timestamp()

    for i in events:
        if i[2] < now:  # если дата события меньше текущего времени
            continue
        dt_object = datetime.datetime.fromtimestamp(i[2]).strftime("%d-%m-%Y %H:%M")
        mk.add(
            InlineKeyboardButton(
                f"{i[3]} [{dt_object}]", callback_data=f"checkevent_{i[0]}"
            )
        )
    adm = checkUserAdmin(user_id)
    if adm == "admin":
        mk.add(
            InlineKeyboardButton("➕ Добавить событие", callback_data="createeventmenu")
        )
    mk.row(mainmenu_btn)
    return mk


def genUserEditMk(user_id):
    mk = InlineKeyboardMarkup(row_width=1)
    banbtn = InlineKeyboardButton("Заблокировать", callback_data=f"banuser_{user_id}")
    unbannbtn = InlineKeyboardButton(
        "Разблокировать", callback_data=f"unbanneduser_{user_id}"
    )
    giveadminbtn = InlineKeyboardButton(
        "Повысить/Разжаловать", callback_data=f"changeadmin_{user_id}"
    )
    givesubtn = InlineKeyboardButton(
        "Подарить подписку", callback_data=f"givesub_{user_id}"
    )
    takesubbtn = InlineKeyboardButton(
        "Забрать подписку", callback_data=f"takesub_{user_id}"
    )
    mk.add(banbtn, unbannbtn, giveadminbtn, givesubtn, takesubbtn, mainmenu_btn)
    return mk


# 1ST DAY IN COMPANY
frstday_mk = InlineKeyboardMarkup(row_width=1)
ofice_access = InlineKeyboardButton("ℹ️ Доступ в офис", callback_data="office_access")
document = InlineKeyboardButton("📖 Договор", callback_data="dogovor")
needed_access = InlineKeyboardButton("🔐 Необходимые доступы", callback_data="needed")
whatsup_chats = InlineKeyboardButton("📱 Чаты Whatsapp", callback_data="whtschats")
frstday_mk.add(ofice_access, document, needed_access, whatsup_chats, mainmenubackbtn)


# ADVERT
advert_mk = InlineKeyboardMarkup(row_width=1)
allad = InlineKeyboardButton("Всем", callback_data="advertforall")
paidad = InlineKeyboardButton("С доступом", callback_data="advertforpaid")
freead = InlineKeyboardButton("Без доступа", callback_data="advertforfree")
advert_mk.add(allad, paidad, freead, mainmenu_btn)


# PAYMENT
payment_mk = InlineKeyboardMarkup(row_width=1)
open_access = InlineKeyboardButton(
    "Оплата в день открытых дверей", callback_data="buysub_open"
)
# test_access = InlineKeyboardButton("Тестовая подписка", callback_data="buysub_test")
month_access = InlineKeyboardButton("1 месяц", callback_data="buysub_month")
three_access = InlineKeyboardButton("3 месяца", callback_data="buysub_three")
halfyear_access = InlineKeyboardButton("6 месяцев", callback_data="buysub_halfyear")
year = InlineKeyboardButton("1 год", callback_data="buysub_year")
cancel_sub_btn = InlineKeyboardButton(
    "❌ Отключить подписку", callback_data="sub_pay_cancel"
)
payment_mk.add(
    # test_access,
    open_access,
    month_access,
    # halfyear_access,
    year,
    # three_access,
)
# payment_mk.row(year)
payment_mk.row(cancel_sub_btn)
payment_mk.row(mainmenubackbtn)


def genPaymentMk(id, link):
    mk = InlineKeyboardMarkup(row_width=1)
    pay = InlineKeyboardButton("💳 Оплатить", url=link)
    check = InlineKeyboardButton("🕰 Проверить оплату", callback_data=f"checkdep_{id}")
    mk.add(pay)
    # mk.add(check)
    return mk



def month_subscription_services_kb():
    buttons = [
        InlineKeyboardButton("🏢 Офис", url="https://telegra.ph/Ofis-DomosKlab-12-20"),
        InlineKeyboardButton("🤖 Чат-бот", url="https://telegra.ph/CHat-bot-DomosKlab-12-20"),
        InlineKeyboardButton("⚖️ Юрист", url="https://telegra.ph/YUrist-DomosKlab--YAna-12-18"),
        InlineKeyboardButton("💰 Налоговый консультант", url="https://telegra.ph/Nalogovyj-konsultant-DomosKlab--Ulyana-12-18"),
        InlineKeyboardButton("👩‍💼 Офис-менеджер", url="https://telegra.ph/Ofis-menedzher-DomosKlab--Olga-12-18"),
        InlineKeyboardButton("📊 CRM и объекты", url="https://telegra.ph/Irina--soprovozhdenie-obektov-i-CRM-12-18"),
        InlineKeyboardButton("🎉 Мероприятия", url="https://telegra.ph/Meropriyatiya-DomosKlab-12-24"),
        InlineKeyboardButton("🧠 Психолог", url="https://telegra.ph/Psiholog-DomosKlab--Olga-12-18"),
        InlineKeyboardButton("🎓 Обучение", url="https://vk.com/club233320734"),
        InlineKeyboardButton("📸 Фотосессия", url="https://telegra.ph/Studiya-DomosKlab-12-20"),
        InlineKeyboardButton("⏳ 12 недель", url="https://telegra.ph/12-nedel-12-24"),
        InlineKeyboardButton("🌅 Магия утра", url="https://telegra.ph/Magiya-utra-DomosKlab-12-24"),
        InlineKeyboardButton("🎊 Корпоративы", url="https://telegra.ph/Korporativy-DomosKlab-12-24"),
        InlineKeyboardButton("📚 Шпаргалка риелтора", url="https://telegra.ph/SHpargalka-rieltora-12-24"),
    ]

    keyboard = [
        buttons[i:i + 2] for i in range(0, len(buttons), 2)
    ]

    keyboard += [
        [InlineKeyboardButton("⬅️ Назад", callback_data="mainmenu")],
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# NEEDED ACCESS
neededaccess_mk = InlineKeyboardMarkup(row_width=2)
crm = InlineKeyboardButton("СРМ", callback_data="crm")
domclick = InlineKeyboardButton("ДомКлик", callback_data="domclick")
upn = InlineKeyboardButton("УПН", callback_data="upn")
nmarket = InlineKeyboardButton("Нмаркет", callback_data="nmarket")
avito = InlineKeyboardButton("Авито", callback_data="avito")
neededaccess_mk.add(crm, domclick, upn, nmarket, avito)
neededaccess_mk.row(firstdaybackbtn)


# WHATSUP CHATS
whatsup_mk = InlineKeyboardMarkup(row_width=2)
domos = InlineKeyboardButton(
    "Домос", url="https://chat.whatsapp.com/F4EDN3gc97b3K0lJBdwNPb"
)
domos_public = InlineKeyboardButton(
    "Домос Паблик", url="https://chat.whatsapp.com/CtTNfFwmQlPErG4MwDHeLh"
)
bla_bl = InlineKeyboardButton(
    "Бла бл...", url="https://chat.whatsapp.com/IpDzDGGsNUhCq4xNONbt0u"
)
reklama = InlineKeyboardButton(
    "Реклама", url="https://chat.whatsapp.com/JxaNvh68UVZEYwviXgN6ol"
)
urist = InlineKeyboardButton(
    "Юрист", url="https://chat.whatsapp.com/H74A2WmONXaEYd0qQhZ8NA"
)
novostroyky = InlineKeyboardButton(
    "Новостройки", url="https://chat.whatsapp.com/KyKi3gD4VdxDOerQQxma6u"
)
whatsup_mk.add(domos, domos_public, bla_bl, reklama, urist, novostroyky)
whatsup_mk.row(firstdaybackbtn)


# RULES
rules_mk = InlineKeyboardMarkup(row_width=1)
manager_ofice_btn = InlineKeyboardButton(
    "Офис менеджер", url="https://telegra.ph/Ofis-menedzher-12-08-6"
)
lawyer_btn = InlineKeyboardButton("Юрист", url="https://telegra.ph/YUrist-12-08")
goodwibe_btn = InlineKeyboardButton(
    "Менеджер хорошего настроения", url="https://telegra.ph/Bi-heppi-menedzher-12-08"
)
manager_soprovoz = InlineKeyboardButton(
    "Менеджер сопровождения", url="https://telegra.ph/Menedzher-soprovozhdeniya-11-20"
)
advertizeAndPay_btn = InlineKeyboardButton(
    "Размещение и оплата рекламы",
    url="https://telegra.ph/Razmeshchenie-oplaty-i-reklamy-12-08",
)
partnershik_btn = InlineKeyboardButton(
    "Партнерщик", url="https://telegra.ph/Zastrojshchiki-12-08"
)
avans_btn = InlineKeyboardButton(
    "Аванс/задаток", url="https://telegra.ph/Avanszadatok-12-08"
)
howDogovor_btn = InlineKeyboardButton(
    "Как заключить договор с клиентом",
    url="https://telegra.ph/Kak-zaklyuchit-dogovor-12-08",
)
educations_btn = InlineKeyboardButton(
    "Обучения", url="https://telegra.ph/Obucheniya-12-08"
)
mission_btn = InlineKeyboardButton(
    "Миссия и ценности", url="https://telegra.ph/Missiya-i-cennosti-12-08"
)
rules_mk.add(
    manager_soprovoz,
    manager_ofice_btn,
    # partnershik_btn,
    goodwibe_btn,
    lawyer_btn,
    advertizeAndPay_btn,
    avans_btn,
    howDogovor_btn,
    educations_btn,
    mission_btn,
)
rules_mk.row(mainmenubackbtn)


# HELPFUL
helpful_mk = InlineKeyboardMarkup(row_width=1)
bt1 = InlineKeyboardButton("Полезные ссылки", callback_data="helpfullinks")
bt2 = InlineKeyboardButton("Доступ в Контур", callback_data="konturaccess")
bt3 = InlineKeyboardButton("Контакты", callback_data="contacntshelpful")
bt4 = InlineKeyboardButton(
    "История компании", url="https://telegra.ph/Istoriya-kompanii-12-08"
)
bt5 = InlineKeyboardButton("Бланки документов", callback_data="helpfulblancs")
# partgivesbtn = InlineKeyboardButton('Партнеры/Бонусы', callback_data='partnersbonuses')
bt6 = InlineKeyboardButton(
    "Подготовка квартиры к съемке", callback_data="helpfulhomephoto"
)
bt7 = InlineKeyboardButton(
    "Памятка по заполнению ТК и 2НДФЛ", callback_data="helpfultk2ndfl"
)
bt8 = InlineKeyboardButton(
    "Команда специалистов ДОМОС", callback_data="helpfulrieltorslist"
)
bt9 = InlineKeyboardButton(
    "Ипотечный калькулятор",
    url="https://docs.google.com/spreadsheets/d/1JBUPAAUilnkoSYkEd5z0tvZulYOVrnCGXgvNnHvyITw/edit",
)
bt10 = InlineKeyboardButton(
    "Вопрос/ответ по самозанятости", url="https://vslebedev.wixsite.com/samozanyatie"
)
bt11 = InlineKeyboardButton(
    "Бонус за друга", url="https://telegra.ph/Privedi-druga-12-28"
)
bt12 = InlineKeyboardButton(
    "Открытки поздравления", url="https://telegra.ph/Otkrytki-12-28"
)
helpful_mk.add(bt1, bt3, bt4, bt5, bt6, bt7, bt8, bt10, bt11, bt12)
helpful_mk.row(mainmenubackbtn)


# ПАРТНЕРЫ/БОНУСЫ
partnersmk = InlineKeyboardMarkup(row_width=1)
bt1 = InlineKeyboardButton(
    "Отделка/ремонты", url="https://telegra.ph/Otdelka-i-remont-03-22"
)
bt2 = InlineKeyboardButton(
    "Грузим/Возим (переезды)", url="https://telegra.ph/Pereezdy-03-22"
)
bt3 = InlineKeyboardButton(
    "Партнеры Дубай/Турция/Грузия",
    url="https://telegra.ph/Zarubezhnaya-nedvizhimost-03-22",
)
bt4 = InlineKeyboardButton(
    "Партнер Москва/Питер/Сочи", url="https://telegra.ph/Goroda-Rossii-03-22"
)
bt5 = InlineKeyboardButton(
    "Ваучер в Турцию БЕСПЛАТНО", url="https://telegra.ph/Vaucher-Turciya-03-22"
)
partnersmk.add(bt1, bt2, bt3, bt4, bt5, mainmenubackbtn)

# HELPFUL LINKS
links_mk = InlineKeyboardMarkup(row_width=1)
banks = InlineKeyboardButton(
    "Таблица Банки",
    url="https://docs.google.com/spreadsheets/d/13TIqojy2J-6BhPhLUy78gswZHH8USQl4dsK0otKtKMM/edit?usp=sharing",
)
novostroyky_table = InlineKeyboardButton(
    "Таблица Новостройки",
    url="https://docs.google.com/spreadsheets/d/1QilOIpu6eHajeN-wZy0a_JyxkZNzVz2h2D5SJHRY6qw/edit?usp=sharing",
)
presentsnew = InlineKeyboardButton(
    "Презентации новостроек",
    url="https://drive.google.com/drive/folders/1vlwuh_dw_YrxLKoKYzJ2Cv_TWGV3tcND?usp=sharing",
)
videosevents = InlineKeyboardButton(
    "Видео с наших мероприятий",
    url="https://drive.google.com/drive/folders/1-1U9PE5ogC3aAIpCLjiCZUi4rx2XI94z?usp=sharing",
)
reviews_yandex = InlineKeyboardButton(
    "Отзывы яндекс",
    url="https://yandex.ru/maps/org/domos/5210005134/reviews/?ll=60.598324%2C56.831634&z=13",
)
prezents_nov = InlineKeyboardButton(
    "Презентации новостроек",
    url="https://drive.google.com/drive/folders/1vlwuh_dw_YrxLKoKYzJ2Cv_TWGV3tcND?usp=share_link",
)
# events_video = InlineKeyboardButton('Видео мероприятий', url='https://drive.google.com/drive/folders/1-1U9PE5ogC3aAIpCLjiCZUi4rx2XI94z')
reviews_google = InlineKeyboardButton("Отзывы Google", url="https://g.co/kgs/rRmufM")
reviews_flamp = InlineKeyboardButton(
    "Отзывы фламп", url="https://ekaterinburg.flamp.ru/domos"
)
vkgroup = InlineKeyboardButton("Группа VK", url="https://vk.com/domosclub")
insta = InlineKeyboardButton(
    "Наш Instagram",
    url="https://www.instagram.com/domos__club?igsh=MTdqZTR6bHk1NG9qbg==",
)
ourweb = InlineKeyboardButton("Наш сайт", url="https://domos.club/")
links_mk.add(
    banks,
    novostroyky_table,
    bt9,
    prezents_nov,
    reviews_yandex,
    reviews_google,
    reviews_flamp,
    vkgroup,
    insta,
    ourweb,
)
links_mk.row(helpfulbackbtn)


# HELPFUL BLANKS
helpfulblanks_mk = InlineKeyboardMarkup(row_width=1)
bt1 = InlineKeyboardButton("Авансовое соглашние", callback_data="helpfulblank1")
bt2 = InlineKeyboardButton("Договор аренды ", callback_data="helpfulblank2")
bt3 = InlineKeyboardButton("Ипотека", callback_data="helpfulblank3")
bt4 = InlineKeyboardButton("Обмен", callback_data="helpfulblank4")
bt5 = InlineKeyboardButton("ПДКП", callback_data="helpfulblank5")
bt6 = InlineKeyboardButton("Подбор", callback_data="helpfulblank6")
bt7 = InlineKeyboardButton("Продажа", callback_data="helpfulblank7")
bt8 = InlineKeyboardButton("Расторжение договора услуг", callback_data="helpfulblank8")
bt9 = InlineKeyboardButton("ЮР СОПР", callback_data="helpfulblank9")

bt10 = InlineKeyboardButton(
    "Соглашение о расторжении аванса", callback_data="helpfulblank10"
)
bt11 = InlineKeyboardButton(
    "Уведомление завышения/занижения краткое", callback_data="helpfulblank11"
)
bt12 = InlineKeyboardButton(
    "Уведомление завышения/занижения полное", callback_data="helpfulblank12"
)
bt13 = InlineKeyboardButton(
    "Уведомление о перепланировке", callback_data="helpfulblank13"
)
bt14 = InlineKeyboardButton("Акт выполненных работ", callback_data="helpfulblank14")
bt15 = InlineKeyboardButton("Согласие на обработку", callback_data="helpfulblank15")
helpfulblanks_mk.add(
    bt1, bt2, bt3, bt4, bt5, bt6, bt7, bt8, bt9, bt10, bt11, bt12, bt13, bt14, bt15
)
helpfulblanks_mk.row(helpfulbackbtn)

helpfulblanks1_mk = InlineKeyboardMarkup(row_width=1)
bt1 = InlineKeyboardButton("Авансовое соглашние", callback_data="blank_1")
bt2 = InlineKeyboardButton("Договор аренды ", callback_data="blank_2")
bt3 = InlineKeyboardButton("Ипотека", callback_data="blank_3")
bt4 = InlineKeyboardButton("Обмен", callback_data="blank_4")
bt6 = InlineKeyboardButton("Подбор", callback_data="blank_6")
bt7 = InlineKeyboardButton("Продажа", callback_data="blank_7")
bt8 = InlineKeyboardButton("Расторжение договора услуг", callback_data="blank_8")
bt9 = InlineKeyboardButton("ЮР СОПР", callback_data="blank_9")
bt10 = InlineKeyboardButton("Соглашение о расторжении аванса", callback_data="blank_10")
helpfulblanks1_mk.add(bt1, bt2, bt3, bt4, bt6, bt7, bt8, bt9, bt10)
helpfulblanks1_mk.row(mainmenu_btn)


def genTimePartsMk(meeting_id):
    times = checkTimes(meeting_id)  # Времена, выбранные текущим пользователем
    roomnum = checkRoom(meeting_id)
    date = checkMeetingDay(meeting_id, roomnum)
    time_mk = InlineKeyboardMarkup(row_width=2)

    # Получаем словарь занятых времен {время: имя_пользователя}
    occupied_times = checkTimeExists1(date, roomnum)
    time_slots = [
        ("9:00-9:30", f"writetime_9:00-9:30_{meeting_id}"),
        ("9:30-10:00", f"writetime_9:30-10:00_{meeting_id}"),
        ("10:00-10:30", f"writetime_10:00-10:30_{meeting_id}"),
        ("10:30-11:00", f"writetime_10:30-11:00_{meeting_id}"),
        ("11:00-11:30", f"writetime_11:00-11:30_{meeting_id}"),
        ("11:30-12:00", f"writetime_11:30-12:00_{meeting_id}"),
        ("12:00-12:30", f"writetime_12:00-12:30_{meeting_id}"),
        ("12:30-13:00", f"writetime_12:30-13:00_{meeting_id}"),
        ("13:00-13:30", f"writetime_13:00-13:30_{meeting_id}"),
        ("13:30-14:00", f"writetime_13:30-14:00_{meeting_id}"),
        ("14:00-14:30", f"writetime_14:00-14:30_{meeting_id}"),
        ("14:30-15:00", f"writetime_14:30-15:00_{meeting_id}"),
        ("15:00-15:30", f"writetime_15:00-15:30_{meeting_id}"),
        ("15:30-16:00", f"writetime_15:30-16:00_{meeting_id}"),
        ("16:00-16:30", f"writetime_16:00-16:30_{meeting_id}"),
        ("16:30-17:00", f"writetime_16:30-17:00_{meeting_id}"),
        ("17:00-17:30", f"writetime_17:00-17:30_{meeting_id}"),
        ("17:30-18:00", f"writetime_17:30-18:00_{meeting_id}"),
        ("18:00-18:30", f"writetime_18:00-18:30_{meeting_id}"),
        ("18:30-19:00", f"writetime_18:30-19:00_{meeting_id}"),
        ("19:00-19:30", f"writetime_19:00-19:30_{meeting_id}"),
        ("19:30-20:00", f"writetime_19:30-20:00_{meeting_id}"),
    ]

    buttons = []
    for time_slot, callback_data in time_slots:
        if time_slot in occupied_times:
            button_text = f"{time_slot} (@{occupied_times[time_slot]})"
        else:
            button_text = time_slot
        buttons.append(InlineKeyboardButton(button_text, callback_data=callback_data))

    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            time_mk.row(buttons[i], buttons[i + 1])
        else:
            time_mk.row(buttons[i])

    time_mk.row(InlineKeyboardButton("◀️ главное меню", callback_data="mainmenu"))
    return time_mk


def feedbackAdmGen(user_id):
    feedback_mk = InlineKeyboardMarkup()
    bt1 = InlineKeyboardButton("Ответить", callback_data=f"feedbackanswer_{user_id}")
    feedback_mk.add(bt1)
    return feedback_mk


def genRieltorsList(page, items_per_page=25):
    mk = InlineKeyboardMarkup(row_width=1)
    rieltors = getRieltors()

    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    rieltors_page = rieltors[start_index:end_index]

    for i in rieltors_page:
        mk.add(InlineKeyboardButton(
            i.get("full_name", "Без имени"), 
            callback_data=f"showrieltor_{i.get('id', '')}"
            ))

    navigation_buttons = []
    if page > 1:
        prev_button = InlineKeyboardButton(
            "◀️ Предыдущая страница", callback_data=f"rieltors_page_{page - 1}"
        )
        navigation_buttons.append(prev_button)

    if end_index < len(rieltors):
        next_button = InlineKeyboardButton(
            "Следущая страница ▶️", callback_data=f"rieltors_page_{page + 1}"
        )
        navigation_buttons.append(next_button)

    if navigation_buttons:
        mk.row(*navigation_buttons)

    mk.add(helpfulbackbtn)
    return mk


def genContactsList():
    mk = InlineKeyboardMarkup(row_width=1)
    contacts = getContacts()
    for i in contacts:
        mk.add(InlineKeyboardButton(
            i.get("full_name", "Без имени"), 
            callback_data=f"showcontacts_{i.get('id', '')}"
            ))
    mk.add(helpfulbackbtn)
    return mk
