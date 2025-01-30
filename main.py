import asyncio
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
import os
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from app.database.models import async_main
from app.hendlers import router as user_router
from app.admin import admin as admin_router

async def main():
    load_dotenv()
    await async_main()

    bot = Bot(token=os.getenv('TOKEN'))
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем обработчики
    dp.include_routers(user_router, admin_router) # Пользовательские обработчики

    # Устанавливаем команды бота
    await bot.set_my_commands([
        BotCommand(command="my_business", description="Моя компания"),
    ])

    await dp.start_polling(bot)





if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
