from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_feedback_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍", callback_data="like"),
            InlineKeyboardButton(text="👎", callback_data="dislike")
        ]
    ])

def get_consultant_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="👨💻 Консультант", callback_data="request_human")
    return builder.as_markup()