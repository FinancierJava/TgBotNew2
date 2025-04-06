from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from app.database import crud, sessions, models
import matplotlib.pyplot as plt
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("report"))
async def report_handler(message: Message):
    async with sessions.AsyncSessionLocal() as db:
        user = await crud.get_or_create_user(db, message.from_user.id)
        if not user.is_admin:
            return

        conversations = db.query(models.Conversation).filter(
            models.Conversation.is_successful == False
        ).all()

        if not conversations:
            await message.answer("⛔ Нет активных запросов в поддержку")
            return

        for conv in conversations:
            
            await db.refresh(conv, ['user'])

            
            history = "\n".join([f"{'Bot' if m['is_bot'] else 'User'}: {m['text']}" for m in conv.messages])
            await message.answer(
                f"🆘 Запрос в поддержку #ID{conv.id}\n"
                f"User ID: {conv.user.telegram_id}\n"
                f"История:\n{history}"
            )


async def is_admin(message: Message) -> bool:
    async with sessions.AsyncSessionLocal() as db:
        user = await crud.get_or_create_user(db, message.from_user.id)
        return user.is_admin


# @router.message(Command("add_admin"))
# async def add_admin_handler(message: Message, command: CommandObject):
#     if not await is_admin(message):
#         return
#
#     if not command.args or not command.args.isdigit():
#         return await message.answer("❌ Укажите ID пользователя: /add_admin <user_id>")
#
#     target_id = int(command.args)
#     async with sessions.AsyncSessionLocal() as db:
#         target_user = await crud.update_user_admin_status(db, target_id, True)
#
#     if target_user:
#         await message.answer(f"✅ Пользователь {target_id} назначен администратором")
#         await message.bot.send_message(
#             target_id,
#             "🎉 Вам выданы права администратора!"
#         )
#     else:
#         await message.answer("❌ Пользователь не найден")
#
#
# @router.message(Command("remove_admin"))
# async def remove_admin_handler(message: Message, command: CommandObject):
#     if not await is_admin(message):
#         return
#
#     if not command.args or not command.args.isdigit():
#         return await message.answer("❌ Укажите ID пользователя: /remove_admin <user_id>")
#
#     target_id = int(command.args)
#     if message.from_user.id == target_id:
#         return await message.answer("❌ Нельзя снять права с самого себя")
#
#     async with sessions.AsyncSessionLocal() as db:
#         target_user = await crud.update_user_admin_status(db, target_id, False)
#
#     if target_user:
#         await message.answer(f"✅ Пользователь {target_id} лишен прав администратора")
#         await message.bot.send_message(
#             target_id,
#             "😞 Ваши права администратора были отозваны"
#         )
#     else:
#         await message.answer("❌ Пользователь не найден")


# app/database/crud.py
from sqlalchemy.future import select
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from io import BytesIO


async def get_conversation_stats(db, period:int = 7):
    """Получение статистики по категориям за указанный период"""
    # Определяем временной диапазон
    now = datetime.now()
    start_date = now - timedelta(days=period)
    # Выполняем запрос к БД
    stmt = (
        select(
            models.Conversation.category,
            func.count(models.Conversation.id).label('count')
        )
        .where(
            and_(
                models.Conversation.start_time >= start_date,
                models.Conversation.end_time.is_not(None)
            )
        )
        .group_by(models.Conversation.category)
    )

    result = await db.execute(stmt)
    stats = result.all()

    return {category: count for category, count in stats}


async def generate_category_pie_chart(db, period: int = 7):
    """Генерация круговой диаграммы по категориям"""
    # Получаем статистику
    stats = await get_conversation_stats(db, period)

    # Подготовка данных для визуализации
    categories = list(stats.keys())
    counts = list(stats.values())

    # Настройка графика
    plt.figure(figsize=(10, 8))
    plt.pie(
        counts,
        labels=categories,
        autopct='%1.1f%%',
        startangle=90,
        colors=plt.cm.Paired.colors,
        wedgeprops={'edgecolor': 'white', 'linewidth': 0.5}
    )
    plt.title(f'Распределение диалогов по категориям\n(Период: {period} дней)', pad=20)

    # Сохраняем в буфер и очищаем график
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)  # Перемотка в начало буфера
    plt.close()  # Закрываем график для освобождения памяти

    return buf


async def get_total_conversations(db, period: int = 7) -> int:
    """Получение общего количества диалогов за период"""
    now = datetime.now()
    start_date = now - timedelta(days=period)

    stmt = (
        select(func.count(models.Conversation.id))
        .where(
            and_(
                models.Conversation.start_time >= start_date,
                models.Conversation.end_time.is_not(None)
            )
        )
    )

    result = await db.execute(stmt)
    return result.scalar()


async def generate_total_conversations_plot(db, period: int = 7) -> BytesIO:
    """Генерация графика с общим количеством диалогов"""
    total = await get_total_conversations(db, period)

    # Создаем минималистичный график
    plt.style.use('seaborn')
    plt.rcParams['font.family'] = 'DejaVu Sans'
    fig, ax = plt.subplots(figsize=(8, 4))

    # Простой текстовый вывод с визуальным оформлением
    ax.text(
        0.5, 0.6,
        f'{total}',
        fontsize=48,
        ha='center',
        va='center',
        color='#2c7bb6'
    )
    ax.text(
        0.5, 0.3,
        f'диалогов за {period} дней',
        fontsize=14,
        ha='center',
        va='center',
        color='#4a4a4a'
    )

    # Убираем оси
    ax.axis('off')

    # Сохраняем в буфер
    buf = BytesIO()
    plt.savefig(
        buf,
        format='png',
        dpi=100,
        bbox_inches='tight',
        pad_inches=0.2
    )
    buf.seek(0)
    plt.close(fig)

    return buf








