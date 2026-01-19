from aiogram.dispatcher.filters.state import StatesGroup, State


class createMeetingStates(StatesGroup):
    roomnum_state = State()
    meeting_id = State()


class feedBackStates(StatesGroup):
    text = State()
    admin_text = State()
    admin_userid = State()
    # feedback_id = State()


class advertismentStates(StatesGroup):
    text = State()
    photo = State()
    adtype = State()


class addRieltorStates(StatesGroup):
    fullname = State()
    phone = State()
    email = State()
    photo = State()


class addEventStates(StatesGroup):
    title = State()
    name = State()
    desc = State()
    date = State()
    link = State()
    timestr = State()


class addContactStates(StatesGroup):
    fullname = State()
    phone = State()
    email = State()
    photo = State()
    job = State()


class searchUserStates(StatesGroup):
    username = State()
    user_id = State()
    months = State()


class createDepositState(StatesGroup):
    payment_link = State()
    payment_id = State()
    price = State()
    fullname = State()


class request_from_db_state(StatesGroup):
    request_floor = State()
    request_info = State()


class AdvertAdminStates(StatesGroup):
    adding_name = State()
    adding_price = State()
    editing_name = State()
    editing_price = State()
