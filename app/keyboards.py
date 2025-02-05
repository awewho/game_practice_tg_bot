from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                            InlineKeyboardMarkup, InlineKeyboardButton)

from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.requests import get_categories, get_category_item, get_podcategories, get_items_by_podcategory


def business_keyboard(businesses, page: int = 0, items_per_page: int = 1):
    keyboard = InlineKeyboardBuilder()
    
    start = page * items_per_page
    end = start + items_per_page
    page_businesses = businesses[start:end]

    for business in page_businesses:
        keyboard.add(
            InlineKeyboardButton(
                text=f"{business.type} | {business.name}" ,
                callback_data=f"business_{business.id}"
            )
        )
    keyboard.adjust(2)

    # Добавляем навигационные кнопки
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_business_{page - 1}"))
    if end < len(businesses):
        navigation_buttons.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"page_business_{page + 1}"))

    if navigation_buttons:
        keyboard.row(*navigation_buttons)

    return keyboard.as_markup()


def user_command():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сделать заказ у поставщика", callback_data="make_order")],
        [InlineKeyboardButton(text="Заключить договор", callback_data="make_contract")],
        [InlineKeyboardButton(text="Заплатить налоги", callback_data="pay_taxes")],
        [InlineKeyboardButton(text="Страховка", callback_data="insurance")]
    ])

def confirm_contract_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_contract")],
        [InlineKeyboardButton(text="Отменить", callback_data="cancel_contract")]
    ])

def confirm_partner_contract_keyboard(initiator_business_id, amount):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_partner_contract_{initiator_business_id}_{amount}")],
        [InlineKeyboardButton(text="Отклонить", callback_data=f"reject_partner_contract_{initiator_business_id}")]
    ])





async def categories():
    all_categories = await get_categories()
    if not all_categories:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Категорий пока нет", callback_data="no_categories")]
        ])
    keyboard = InlineKeyboardBuilder()
    
    for category in all_categories:
        # Убедимся, что callback_data короткая и допустимая
        keyboard.add(InlineKeyboardButton(
            text=category.name,
            callback_data=f"category_{category.id}"  # Убедись, что category.id — это число
        ))
    keyboard.row(InlineKeyboardButton(text='На главную', callback_data='to_main'))
    return keyboard.adjust(2).as_markup()

async def podcategories(category_id):
    podcategories = await get_podcategories(category_id)
    podcategories_list = podcategories.all() 
    if not podcategories_list:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подкатегорий пока нет", callback_data="no_podcategories")]
        ])
    
    keyboard = InlineKeyboardBuilder()

    # Добавляем подкатегории по 2 в строку
    for podcategory in podcategories_list:
        keyboard.add(InlineKeyboardButton(
            text=podcategory.name,
            callback_data=f"podcategory_{podcategory.id}"
        ))

    # Если количество подкатегорий нечетное, последняя кнопка будет занимать всю ширину
    if len(podcategories_list) % 2 != 0:
        keyboard.adjust(2, 2, 1)  # 2 столбца, 2 строки, последняя кнопка на всю ширину
    else:
        keyboard.adjust(2)  # 2 столбца

    # Добавляем кнопку "Назад"
    keyboard.row(InlineKeyboardButton(text='К категориям', callback_data='to_categories'))

    return keyboard.as_markup()

async def items(podcategory_id, page: int = 0, items_per_page: int = 6):
    all_items = await get_items_by_podcategory(podcategory_id)
    
    keyboard = InlineKeyboardBuilder()

    start = page * items_per_page
    end = start + items_per_page
    page_items = all_items[start:end]

    # Добавляем товары по 2 в строку
    for item in page_items:
        keyboard.add(InlineKeyboardButton(
            text=item.name[:20],  # Обрезаем название, если оно слишком длинное
            callback_data=f"item_{item.id}"
        ))

    # Навигационные кнопки
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_items_{page - 1}"))
    if end < len(all_items):
        navigation_buttons.append(InlineKeyboardButton(text="➡️ Вперёд", callback_data=f"page_items_{page + 1}"))

    if navigation_buttons:
        keyboard.row(*navigation_buttons)

    # Добавляем кнопку "Назад" в подкатегорию
    keyboard.row(InlineKeyboardButton(text='К категориям', callback_data='to_categories'))

    # Настраиваем 2 столбца
    keyboard.adjust(2)

    return keyboard.as_markup()


def add_or_order_keyboard():
    """Клавиатура с кнопками 'Оформить заказ' и 'Добавить ещё товары'."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оформить заказ", callback_data="show_cart")],
        [InlineKeyboardButton(text="Добавить ещё товары", callback_data="make_order")]
    ])

def confirm_order_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить заказ", callback_data="confirm_order")],
        [InlineKeyboardButton(text="Отменить заказ", callback_data="cancel_order")]
    ])




def admin_keyboard():
    """Клавиатура для администратора."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Списать затраты", callback_data="deduct_expenses")],
        [InlineKeyboardButton(text="Добавить деньги", callback_data="add_money")],
        [InlineKeyboardButton(text="Снять деньги", callback_data="remove_money")],    
        [InlineKeyboardButton(text='Обновить ежемесячные затраты', callback_data="update_expenses")],
        [InlineKeyboardButton(text='Сделать отчет', callback_data="create_report")],
        [InlineKeyboardButton(text='Инфляция +15%', callback_data="inflation")]
    ])


