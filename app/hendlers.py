from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart,Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import Bot


import app.keyboards as kb


import app.database.requests as rq

router = Router()

class Registration(StatesGroup):
    business_name = State()  # Изменение названия бизнеса

class Quantity(StatesGroup):
    awaiting_quantity = State()


async def send_message_to_channel(bot: Bot, text: str):

    """Отправляет сообщение в канал."""
    await bot.send_message(chat_id= os.getenv('CHANNEL_ID'), text=text)



@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обрабатывает команду /start и выводит список бизнесов."""
    businesses = await rq.get_all_businesses()
    if not businesses:
        await message.answer("Нет доступных бизнесов. Обратитесь к администратору.")
        return

    await message.answer(
        "Выберите тип вашего бизнеса:",
        reply_markup=kb.business_keyboard(businesses)
    )



@router.callback_query(StateFilter(None), F.data.startswith("business_"))
async def choose_business(callback: CallbackQuery, state: FSMContext):
    """Привязывает бизнес к пользователю и предлагает изменить название."""
    business_id = int(callback.data.split("_")[1])

    # Привязываем бизнес к пользователю
    await rq.assign_business_to_user(callback.from_user.id, business_id)

    # Сохраняем business_id в FSM для изменения названия
    await state.update_data(business_id=business_id)

    # Запрашиваем ввод нового названия
    await callback.message.answer("Введите новое название вашего бизнеса:")
    await state.set_state(Registration.business_name)


@router.message(StateFilter(Registration.business_name))
async def rename_business(message: Message, state: FSMContext):
    """Сохраняет новое название бизнеса и отправляет сообщение в канал."""
    business_name = message.text
    data = await state.get_data()
    business_id = data.get("business_id")

    # Изменяем название бизнеса
    await rq.rename_business(business_id, business_name)

    # Логируем событие
    await rq.log_event(
        user_id=message.from_user.id,
        event_type="rename_business",
        description=f"Появилась новая компания: {business_name}",
        business_id=business_id
    )

    # Отправляем сообщение в канал
    await send_message_to_channel(
        bot=message.bot,
        text=f"Появилась новая компания: {business_name}"
    )

    await message.answer(f"Название вашего бизнеса успешно изменено на: {business_name}!")
    await state.clear()



@router.callback_query(F.data.startswith("page_"))
async def paginate(callback: CallbackQuery):
    """Универсальный обработчик перелистывания страниц."""
    data = callback.data.split("_")
    page_type = data[1]  # Определяем тип (business или items)
    page = int(data[2])  # Определяем номер страницы

    if page_type == "business":
        # Получаем бизнесы для данной страницы
        businesses = await rq.get_all_businesses()
        await callback.message.edit_text(
            "Выберите тип вашего бизнеса:",
            reply_markup=kb.business_keyboard(businesses, page=page)
        )

    elif page_type == "items":
        # Получаем товары для данной категории
        category_id = int(callback.message.reply_markup.inline_keyboard[0][0].callback_data.split("_")[1])  # Категория берётся из текущей клавиатуры
        await callback.message.edit_text(
            "Выберите товар:",
            reply_markup=await kb.items(category_id, page=page)
        )



@router.message(Command("my_business"))
async def show_business_info(message: Message):
    """Показывает информацию о бизнесе пользователя."""
    user_data = await rq.get_user_with_business(message.from_user.id)
    if not user_data or not user_data.business_id:
        await message.answer("Вы ещё не зарегистрировали бизнес. Пожалуйста, начните с команды /start.")
        return

    business = user_data.business
    response = (
        f"Тип вашего бизнес: {business.type}\n"
        f"Название вашего бизнеса: {business.name}\n"
        f"Текущий бюджет: {business.budget} рублей\n"
        f"Текущие ежемесячные траты: {business.expenses} рублей"
    )
    await message.answer(response, reply_markup=kb.make_order_button())




@router.callback_query(F.data == "make_order")
async def catalog_gen_post(callback: CallbackQuery):
    await callback.message.answer('Выберите категорию товара', reply_markup=await kb.categories())




@router.callback_query(F.data.startswith('category_'))
async def category(callback: CallbackQuery):
    await callback.message.answer('Выберите товар', 
                                reply_markup=await kb.items(callback.data.split('_')[1]))
    


@router.callback_query(StateFilter(None), F.data.startswith('item_'))
async def item(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор товара."""
    item_id = int(callback.data.split('_')[1])
    item_data = await rq.get_item(item_id)

    if not item_data:
        await callback.answer("Товар не найден!", show_alert=True)
        return

    await callback.message.answer(
        f"Вы выбрали товар: {item_data.name}\nОписание: {item_data.description}\nЦена: {item_data.price} рублей.\n\n"
        "Введите количество товара:",
    )

    # Сохраняем item_id в FSM
    await state.update_data(selected_item_id=item_id)

    # Устанавливаем состояние для ожидания количества
    await state.set_state(Quantity.awaiting_quantity)



@router.message(StateFilter(Quantity.awaiting_quantity))
async def set_quantity(message: Message, state: FSMContext):
    """Обрабатывает ввод количества товара."""
    try:
        quantity = int(message.text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректное количество (целое число больше 0).")
        return

    # Получаем данные из FSM
    data = await state.get_data()
    item_id = data.get("selected_item_id")

    # Добавляем товар в корзину
    await rq.add_to_cart(message.from_user.id, item_id, quantity)

    await message.answer(
        "Товар добавлен в корзину!",
        reply_markup=kb.add_or_order_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "to_main")
async def to_main(callback: CallbackQuery):
    """Обрабатывает кнопку 'На главную'."""
    user_data = await rq.get_user_with_business(callback.from_user.id)
    if not user_data or not user_data.business_id:
        await callback.message.answer("Вы ещё не зарегистрировали бизнес. Пожалуйста, начните с команды /start.")
        return

    business = user_data.business
    response = (
        f"Тип вашего бизнеса: {business.type}\n"
        f"Название вашего бизнеса: {business.name}\n"
        f"Текущий бюджет: {business.budget} рублей\n"
        f"Текущие ежемесячные траты: {business.expenses} рублей"
    )
    await callback.message.answer(response, reply_markup=kb.make_order_button())


@router.callback_query(F.data == "show_cart")
async def show_cart(callback: CallbackQuery):
    """Отображает содержимое корзины."""
    cart_items = await rq.get_cart(callback.from_user.id)
    if not cart_items:
        await callback.message.answer("Ваша корзина пуста.")
        return

    # Формируем текст корзины
    response = "Ваш заказ:\n"
    total_price = 0
    for item, quantity in cart_items:
        response += f"{item.name} x{quantity}шт. = {item.price * quantity} рублей\n"
        total_price += item.price * quantity

    response += f"\nИтоговая сумма: {total_price} рублей."
    await callback.message.answer(response, reply_markup=kb.confirm_order_keyboard())




@router.callback_query(F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery):
    user = await rq.get_user_with_business(callback.from_user.id)
    if not user or not user.business:
        await callback.answer("Ваш бизнес не зарегистрирован.")
        return

    cart_items = await rq.get_cart(callback.from_user.id)
    if not cart_items:
        await callback.message.answer("Ваша корзина пуста.")
        return

    # Подсчитываем итоговую стоимость заказа
    total_price = sum(item.price * quantity for item, quantity in cart_items)

    # Проверяем, хватает ли бюджета для оформления заказа
    if user.business.budget < total_price:
        await callback.message.answer("Недостаточно средств на счете для оформления заказа.")
        return

    # Списываем деньги с бюджета и логируем событие
    await rq.deduct_money_from_business(user.business_id, total_price)

    # Логируем событие
    await rq.log_event(
        user_id=callback.from_user.id,
        event_type="make_order",
        description=f"Компания {user.business.name} сделала закупку на сумму {total_price} рублей",
        business_id=user.business_id
    )

    # Отправляем сообщение в канал
    await send_message_to_channel(
        bot=callback.bot,
        text=f"Компания {user.business.name} сделала закупку на сумму {total_price} рублей"
    )
    
    # Очищаем корзину
    await rq.clear_cart(callback.from_user.id)

    # Подтверждаем заказ пользователю
    await callback.message.answer("Заказ оформлен! Спасибо за покупку.")




@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery):
    """Обрабатывает отмену заказа и очищает корзину."""
    # Очищаем корзину пользователя
    await rq.clear_cart(callback.from_user.id)

    # Уведомляем пользователя
    await callback.message.answer("Ваш заказ отменён. Все товары удалены из корзины.")

