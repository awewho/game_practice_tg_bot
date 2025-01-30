from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter, Filter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
import os
from app.database.requests import deduct_all_expenses, add_money_to_user, get_users
from app.keyboards import admin_keyboard


load_dotenv()
# Идентификатор администратора
ADMIN_ID = os.getenv('ADMIN_ID')

admin = Router()


class AddMoney(StatesGroup):
    awaiting_add_money = State()


class Admin(Filter):
    """Фильтр для проверки, является ли пользователь администратором."""
    async def __call__(self, message: Message) -> bool:
        return message.from_user and message.from_user.id == ADMIN_ID


@admin.message(Admin(), Command("admin"))
async def admin_start(message: Message):
    """Обрабатывает команду /start для администратора."""
    await message.answer(
        "Добро пожаловать в админ-панель. Выберите действие:",
        reply_markup=admin_keyboard()
    )


@admin.callback_query(Admin(), F.data == "deduct_expenses")
async def deduct_expenses(callback: CallbackQuery):
    """Списывает ежемесячные затраты у всех пользователей."""
    total_deducted = await deduct_all_expenses()
    users = await get_users()
    for user in users: 
        try:
            await callback.message.send_copy(chat_id=user.tg_id)
        except Exception as e:
            pass
    await callback.message.answer(f"Списаны ежемесячные затраты на общую сумму {total_deducted} рублей.")
        




@admin.message(Admin(), Command("add_money"))
async def add_money_start(message: Message, state: FSMContext):
    """Начинает процесс добавления денег пользователю."""
    await message.answer("Введите ID пользователя и сумму через пробел (например: 12345 1000):")
    await state.set_state(AddMoney.awaiting_add_money)




@admin.message(Admin(), StateFilter(AddMoney.awaiting_add_money))
async def process_add_money(message: Message, state: FSMContext):
    """Обрабатывает ввод ID пользователя и суммы для добавления денег."""
    try:
        user_id, amount = map(int, message.text.split())
        if amount <= 0:
            raise ValueError

        await add_money_to_user(user_id, amount)
        await message.answer(f"Пользователю с ID {user_id} добавлено {amount} рублей.")
        await state.clear()
    except ValueError:
        await message.answer("Введите корректные данные (ID пользователя и сумма).")




@admin.message(F.text == "На главную", Admin())
async def admin_main_menu(message: Message):
    """Возвращает администратора в главное меню."""
    await message.answer(
        "Вы снова в админ-панели. Выберите действие:",
        reply_markup=admin_keyboard()
    )