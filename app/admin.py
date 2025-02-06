from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter, Filter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from collections import defaultdict

from app.database.requests import deduct_all_expenses, add_money_to_company, get_users, update_monthly_expenses, get_user_with_business, increase_prices_by_15_percent, get_business_by_id
from app.keyboards import admin_keyboard



ADMIN_ID = [753755508, 382900778, 1290399251]
# Идентификатор администратора


admin = Router()



class AddMoney(StatesGroup):
    awaiting_business_id = State()
    awaiting_amount = State()


class RemoveMoney(StatesGroup):
    awaiting_business_id = State()
    awaiting_amount = State()

class UpdateExpenses(StatesGroup):
    awaiting_business_id = State()
    awaiting_new_expenses = State()


class Admin(Filter):
    """Фильтр для проверки, является ли пользователь администратором."""
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in ADMIN_ID



@admin.message(Admin(), Command("admin"))
async def admin_start(message: Message):
    """Обрабатывает команду /start для администратора."""
    await message.answer(
        "Добро пожаловать в админ-панель. Выберите действие:",
        reply_markup=admin_keyboard()
    )


@admin.callback_query(Admin(), F.data == "deduct_expenses")
async def deduct_expenses(callback: CallbackQuery):
    """Списывает ежемесячные затраты у всех пользователей и уведомляет их."""
    total_deducted = await deduct_all_expenses()
    users = await get_users()

    for user in users:
        if user.business:  # Проверяем, что у пользователя есть бизнес
            try:
                # Отправляем персонализированное сообщение
                await callback.bot.send_message(
                    chat_id=user.tg_id,
                    text=f"С вашей компании '{user.business.name}' списаны ежемесячные затраты в размере {user.business.expenses} рублей."
                )
            except Exception as e:
                print(f"Не удалось отправить сообщение пользователю {user.tg_id}: {e}")

    await callback.message.answer(f"Списаны ежемесячные затраты на общую сумму {total_deducted} рублей.")
        



@admin.callback_query(Admin(), F.data == "add_money")
async def add_money_start(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс добавления денег компании."""
    await callback.message.answer("Введите ID компании:")
    await state.set_state(AddMoney.awaiting_business_id)


@admin.message(Admin(), StateFilter(AddMoney.awaiting_business_id))
async def process_business_id(message: Message, state: FSMContext):
    """Обрабатывает ввод ID компании."""
    try:
        business_id = int(message.text)
        if business_id <= 0:
            raise ValueError

        await state.update_data(business_id=business_id)
        await message.answer(f"ID компании установлен: {business_id} название компании \nТеперь введите сумму для пополнения:")
        await state.set_state(AddMoney.awaiting_amount)

    except ValueError:
        await message.answer("Введите корректный числовой ID компании.")



@admin.message(Admin(), StateFilter(AddMoney.awaiting_amount))
async def process_add_money(message: Message, state: FSMContext):
    """Обрабатывает ввод суммы для пополнения и уведомляет владельца компании."""
    data = await state.get_data()
    business_id = data.get("business_id")
    business = await get_business_by_id(business_id)

    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError

        # Добавляем деньги на счет компании
        await add_money_to_company(business_id, amount)
        

        if business and business.users:  # Проверяем, есть ли пользователи у бизнеса
            owner = business.users[0]  # Берем первого владельца

            try:
                # Отправляем уведомление владельцу компании
                await message.bot.send_message(
                    chat_id=owner.tg_id,
                    text=f"💰 На счет вашей компании '{business.name}' поступило {amount} рублей."
                )
            except Exception as e:
                print(f"⚠️ Не удалось отправить сообщение пользователю {owner.tg_id}: {e}")
        else:
            await message.answer(f"⚠️ Внимание: У компании с ID {business_id} нет зарегистрированных владельцев.")
        await message.answer(f"Компании {business.name} получила {amount} рублей")
        await state.clear()

    except ValueError:
        await message.answer("Введите корректную сумму (целое число больше 0).")



@admin.callback_query(Admin(), F.data == "remove_money")
async def remove_money_start(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс снятия денег с компании."""
    await callback.message.answer("Введите ID компании:")
    await state.set_state(RemoveMoney.awaiting_business_id)


@admin.message(Admin(), StateFilter(RemoveMoney.awaiting_business_id))
async def process_business_id(message: Message, state: FSMContext):
    """Обрабатывает ввод ID компании."""
    try:
        business_id = int(message.text)
        if business_id <= 0:
            raise ValueError

        await state.update_data(business_id=business_id)
        await message.answer(f"ID компании установлен: {business_id} название компании \nТеперь введите сумму для снятия:")
        await state.set_state(RemoveMoney.awaiting_amount)

    except ValueError:
        await message.answer("Введите корректный числовой ID компании.")


@admin.message(Admin(), StateFilter(RemoveMoney.awaiting_amount))
async def process_remove_money(message: Message, state: FSMContext):
    """Обрабатывает ввод суммы для снятия и уведомляет владельца компании."""
    data = await state.get_data()
    business_id = data.get("business_id")
    business = await get_business_by_id(business_id)

    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError

        # Снимаем деньги со счета компании
        await remove_money_from_company(business_id, amount)

        if business and business.users:  # Проверяем, есть ли пользователи у бизнеса
            owner = business.users[0]  # Берем первого владельца

            try:
                # Отправляем уведомление владельцу компании
                await message.bot.send_message(
                    chat_id=owner.tg_id,
                    text=f"💰 Со счета вашей компании '{business.name}' было снято {amount} рублей."
                )
            except Exception as e:
                print(f"⚠️ Не удалось отправить сообщение пользователю {owner.tg_id}: {e}")
        else:
            await message.answer(f"⚠️ Внимание: У компании с ID {business_id} нет зарегистрированных владельцев.")
        await message.answer(f"С компании {business.name} было снято {amount} рублей")
        await state.clear()

    except ValueError:
        await message.answer("Введите корректную сумму (целое число больше 0).")


@admin.callback_query(Admin(), F.data == "update_expenses")
async def update_expenses_start(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс обновления ежемесячных затрат."""
    await callback.message.answer("Введите ID бизнеса:")
    await state.set_state(UpdateExpenses.awaiting_business_id)


@admin.message(Admin(), StateFilter(UpdateExpenses.awaiting_business_id))
async def process_business_id(message: Message, state: FSMContext):
    """Обрабатывает ввод ID бизнеса."""
    try:
        business_id = int(message.text)
        await state.update_data(business_id=business_id)
        await message.answer("Введите новую сумму ежемесячных затрат:")
        await state.set_state(UpdateExpenses.awaiting_new_expenses)
    except ValueError:
        await message.answer("Введите корректный ID бизнеса (целое число).")


@admin.message(Admin(), StateFilter(UpdateExpenses.awaiting_new_expenses))
async def process_new_expenses(message: Message, state: FSMContext):
    """Обрабатывает ввод новой суммы ежемесячных затрат."""
    try:
        new_expenses = int(message.text)
        if new_expenses < 0:
            raise ValueError

        data = await state.get_data()
        business_id = data.get("business_id")

        await update_monthly_expenses(business_id, new_expenses)
        await message.answer(f"Ежемесячные затраты для бизнеса с ID {business_id} обновлены на {new_expenses} рублей.")
        await state.clear()
    except ValueError:
        await message.answer("Введите корректную сумму затрат (целое число больше или равно 0).")



@admin.callback_query(Admin(), F.data == "create_report")
async def create_report(callback: CallbackQuery):
    """Делает отчет по текущему балансу всех компаний"""

    users = await get_users()

    if not users:
        await callback.message.answer("В базе данных нет зарегистрированных пользователей.")
        return

    companies = []
    business_summary = defaultdict(list)

    # Собираем данные о компаниях и группируем по типу бизнеса
    for user in users:
        if user.business:  
            name = user.business.name
            business_type = user.business.type
            budget = user.business.budget
            income = user.business.income
            cost = user.business.cost
            profit = income - cost  # Разница между доходом и расходом

            companies.append((name, business_type, budget, income, cost, profit))
            business_summary[business_type].append((name, budget, income, cost, profit))  # Добавляем КОРТЕЖИ

    # Сортируем компании по прибыли (от большего к меньшему)
    companies.sort(key=lambda x: x[4], reverse=True)

    # Формируем первую часть отчета: компании по прибыли
    report = "🏢 Все компании по прибыли (от большего к меньшему):\n\n"
    for idx, (name, business_type, budget, income, cost, profit) in enumerate(companies, 1):
        report += f"{idx}. {name} ({business_type}) — 💰 Бюджет: {budget} ₽,\n 💵 Доход: {income} ₽, 📉 Расход: {cost} ₽, 📊 Прибыль: {profit} ₽\n"

    # Формируем вторую часть отчета: сравнение типов бизнеса
    report += "\n📊 Сравнение по категориям бизнеса:\n\n"
    for business_type, businesses in business_summary.items():
        total_income = sum(income for _, _, income, _, _ in businesses)
        total_cost = sum(cost for _, _, _, cost, _ in businesses)
        total_budget = sum(budget for _, budget, _, _, _ in businesses)        
        avg_budget = total_budget // len(businesses)
        total_profit = total_income - total_cost


        report += (f"{business_type}\n"
                   f"🔹 Количество компаний: {len(businesses)}\n"
                   f"💵 Общий бюджет: {total_budget} ₽\n"
                   f"💰 Общий доход: {total_income} ₽\n"
                   f"📉 Общий расход: {total_cost} ₽\n"
                   f"📊 Общая прибыль: {total_profit} ₽\n"
                   f"🏢 Компании:\n")

        # Добавляем список компаний в этой категории
        for name, budget, income, cost, profit in sorted(businesses, key=lambda x: x[4], reverse=True):
            report += f"   - {name}:  💰 Бюджет: {budget} ₽, 💵 Доход: {income} ₽, 📉 Расход: {cost} ₽, 📊 Прибыль: {profit} ₽\n"  
        report += "\n"  # Отделяем категории

    await callback.message.answer(report)



@admin.callback_query(Admin(), F.data == "inflation")
async def update_expenses_start(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает команду увеличения цен на 15%."""
    try:
        # Увеличиваем цены на 15%
        updated_items_count = await increase_prices_by_15_percent()
        await callback.message.answer(f"✅ Цены на все продукты успешно увеличены на 15%. Обновлено товаров: {updated_items_count}.")
    except Exception as e:
        await callback.message.answer(f"❌ Произошла ошибка при обновлении цен: {e}")