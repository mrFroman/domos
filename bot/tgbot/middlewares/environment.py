from aiogram.dispatcher.middlewares import LifetimeControllerMiddleware, BaseMiddleware
from aiogram import types
from aiogram.dispatcher.handler import CancelHandler


class EnvironmentMiddleware(LifetimeControllerMiddleware):
    skip_patterns = ["error", "update"]
    
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs
    
    async def pre_process(self, obj, data, *args):
        data.update(**self.kwargs)


class PrivateOnlyMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message: types.Message, data: dict):
        if message.chat.type != types.ChatType.PRIVATE:
            raise CancelHandler()
