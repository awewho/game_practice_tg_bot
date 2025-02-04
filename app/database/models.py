from sqlalchemy import BigInteger, String, ForeignKey, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs,async_sessionmaker,create_async_engine
from datetime import datetime

from dotenv import load_dotenv
import os

load_dotenv()

engine = create_async_engine(url=os.getenv('SQLALCHEMY_URL'))

async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger, unique=True)
    business_id: Mapped[int] = mapped_column(ForeignKey('businesses.id'), nullable=True)
    business = relationship(
        'Business',
        back_populates='users',
        lazy='selectin'  # Загружать данные немедленно
    )



class Business(Base):
    __tablename__ = 'businesses'

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(50))  # Тип бизнеса
    name: Mapped[str] = mapped_column(String(50))  # Название компании
    budget: Mapped[int] = mapped_column(Integer, default=0)  # Бюджет
    expenses: Mapped[int] = mapped_column(Integer, default=0)  # Траты
    users = relationship('User', back_populates='business', lazy='selectin')


class Cart(Base):
    __tablename__ = 'cart'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'))
    item_id: Mapped[int] = mapped_column(ForeignKey('items.id'))
    quantity: Mapped[int] = mapped_column(default=1)

    user = relationship('User', back_populates='cart')
    item = relationship('Item')

User.cart = relationship('Cart', back_populates='user', cascade='all, delete-orphan')

class Category(Base):
    __tablename__ = 'categories'

    id: Mapped[int]= mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(25))


class Item(Base):
    __tablename__ = 'items'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(25))

    price: Mapped[int] = mapped_column()
    weight: Mapped[int] = mapped_column(default=0)  # Вес в кг
    category: Mapped[int] = mapped_column(ForeignKey('categories.id'))



class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Добавляем аннотацию типа int
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String)  # Тип события (например, "rename_business" или "make_order")
    description: Mapped[str] = mapped_column(String)  # Подробности события
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # Время события

    user = relationship("User")  # Связь с моделью User
    business = relationship("Business")  # Связь с моделью Business

    

async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)