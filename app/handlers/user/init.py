from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.future import select
from app.database import crud, sessions, models
from app.keyboards import keyboards

router = Router()


@router.message(Command("start"))
async def start_handler(message: Message):
    async with sessions.AsyncSessionLocal() as db:
        await crud.get_or_create_user(db, message.from_user.id)
    await message.answer("👋 Привет! Я AI-ассистент. Задай мне вопрос, и я постараюсь помочь!")


@router.message(~F.text.startswith('/') & F.text)
async def text_message_handler(message: Message):
    async with sessions.AsyncSessionLocal() as db:
        user = await crud.get_or_create_user(db, message.from_user.id)
        conversation = await crud.get_active_conversation(db, user.id)

        if not conversation:
            conversation = await crud.create_conversation(db, user.id)

        conversation = await crud.add_message_to_conversation(db, conversation, message.text, False)
        bot_response = "Hello World! Это тестовый ответ."
        conversation = await crud.add_message_to_conversation(db, conversation, bot_response, True)

        await message.answer(bot_response, reply_markup=keyboards.get_feedback_kb())


@router.callback_query(F.data == "like")
async def like_handler(callback: CallbackQuery):
    async with sessions.AsyncSessionLocal() as db:
        user = await crud.get_or_create_user(db, callback.from_user.id)
        conversation = await crud.get_active_conversation(db, user.id)
        if conversation:
            await crud.complete_conversation(db, conversation, True)

    await callback.message.edit_reply_markup()
    await callback.answer()
    await callback.message.answer("✅ Рад, что смог помочь! Обращайтесь еще!")


@router.callback_query(F.data == "dislike")
async def dislike_handler(callback: CallbackQuery):
    async with sessions.AsyncSessionLocal() as db:
        user = await crud.get_or_create_user(db, callback.from_user.id)
        conversation = await crud.get_active_conversation(db, user.id)
        if conversation:
            await crud.complete_conversation(db, conversation, False)

    await callback.message.edit_reply_markup()
    await callback.answer()
    await callback.message.answer(
        "❌ Извините, что ответ не подошел. Вы можете обратиться к консультанту:",
        reply_markup=keyboards.get_consultant_kb()
    )


@router.callback_query(F.data == "request_human")
async def human_handler(callback: CallbackQuery):
    async with sessions.AsyncSessionLocal() as db:
        user = await crud.get_or_create_user(db, callback.from_user.id)
        conversation = await crud.get_active_conversation(db, user.id)
        if conversation:
            await notify_admins(callback.bot, conversation)

    await callback.message.edit_reply_markup()
    await callback.answer()
    await callback.message.answer("🆘 Ваш запрос передан консультанту. Ожидайте ответа.")


async def notify_admins(bot, conversation):
    async with sessions.AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.User)
            .where(models.User.is_admin == True)
        )
        admins = result.scalars().all()

        history = "\n".join([f"{'Bot' if m['is_bot'] else 'User'}: {m['text']}" for m in conversation.messages])

        for admin in admins:
            await bot.send_message(
                admin.telegram_id,
                f"🚨 НОВЫЙ ЗАПРОС ПОДДЕРЖКИ\n"
                f"User ID: {conversation.user.telegram_id}\n"
                f"История диалога:\n{history}"
            )