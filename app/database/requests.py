from app.database.models import async_session
from app.database.models import User, Category, Item, Business, Cart, Event
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload



def connection(func):
    async def inner(*args, **kwargs):
        async with async_session() as session:
            return await func(session, *args, **kwargs)
    return inner


@connection
async def set_user(session, tg_id):
    user = await session.scalar(select(User).where(User.tg_id == tg_id))
    if not user:
        session.add(User(tg_id=tg_id))
        await session.commit()
    return user


@connection
async def get_all_businesses(session):
    result = await session.scalars(select(Business))
    return result.all()  # Преобразуем ScalarResult в список


@connection
async def assign_business_to_user(session, tg_id, business_id):
    """Привязывает существующий бизнес к пользователю."""
    user = await session.scalar(select(User).where(User.tg_id == tg_id))
        
    if not user:
        # Автоматически создаём пользователя, если он отсутствует
        user = User(tg_id=tg_id)
        session.add(user)
        await session.commit()  # Сохраняем пользователя в базу

    business = await session.scalar(select(Business).where(Business.id == business_id))
    if not business:
        raise ValueError(f"Бизнес с ID {business_id} не найден.")

    user.business_id = business.id
    await session.commit()

@connection
async def rename_business(session, business_id, new_name):
    """Изменяет название бизнеса."""
    business = await session.scalar(select(Business).where(Business.id == business_id))
    if not business:
        raise ValueError(f"Бизнес с ID {business_id} не найден.")

    business.name = new_name
    await session.commit()   

@connection
async def get_user_with_business(session, tg_id):
    """Получает пользователя с привязанным к нему бизнесом."""
    user = await session.scalar(
        select(User).where(User.tg_id == tg_id).options(selectinload(User.business))
    )
    return user


@connection
async def get_users(session):
    """Получает всех пользователей."""
    return await session.scalars(select(User))



@connection 
async def add_to_cart(session, user_id, item_id, quantity):
    """Добавляет товар в корзину."""
    cart_item = await session.scalar(
        select(Cart).where(Cart.user_id == user_id, Cart.item_id == item_id)
    )
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=user_id, item_id=item_id, quantity=quantity)
        session.add(cart_item)
    await session.commit()


@connection
async def get_cart(session, user_id):
    """Возвращает содержимое корзины пользователя."""
    cart_items = await session.execute(
        select(Cart, Item).join(Item).where(Cart.user_id == user_id)
    )
    return [(item, cart_item.quantity) for cart_item, item in cart_items]


@connection
async def deduct_money_from_business(session, business_id, amount):
    """Списывает деньги с бюджета бизнеса."""
    
    business = await session.scalar(select(Business).where(Business.id == business_id))
    if not business:
        raise ValueError(f"Бизнес с ID {business_id} не найден.")

        # Проверяем, хватает ли бюджета
    if business.budget < amount:
        raise ValueError(f"Недостаточно средств. Бюджет: {business.budget}, требуется: {amount}")

        # Списываем деньги
    business.budget -= amount
    await session.commit()
        

@connection
async def clear_cart(session, user_id):
    await session.execute(delete(Cart).where(Cart.user_id == user_id))
    await session.commit()




@connection
async def get_categories(session):
    return await session.scalars(select(Category))


@connection
async def get_category_item(session, category_id):
    result = await session.scalars(select(Item).where(Item.category == category_id))
    return result.all()
        

@connection
async def get_item(session,item_id):
    return await session.scalar(select(Item).where(Item.id == item_id))


@connection
async def log_event(session, user_id, event_type, description, business_id=None):
    """Логирует событие в базу данных."""
    event = Event(
        user_id=user_id,
        business_id=business_id,
        event_type=event_type,
        description=description
    )
    session.add(event)
    await session.commit()



@connection
async def add_money_to_user(session, user_id, amount):
    """Добавляет деньги пользователю."""
    user = await session.scalar(select(User).where(User.id == user_id))
    if not user or not user.business:
        raise ValueError("Пользователь или бизнес не найден.")
    user.business.budget += amount
    await session.commit()

@connection
async def deduct_all_expenses(session):
    users = await session.scalars(
        select(User)
        .options(selectinload(User.business))  # Явно загружаем связанные данные
        .where(User.business_id.isnot(None))
    )
    total_deducted = 0

    for user in users:
        business = user.business
        if business and business.budget >= business.expenses:
            business.budget -= business.expenses
            total_deducted += business.expenses

    await session.commit()
    return total_deducted