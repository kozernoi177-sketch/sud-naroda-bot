from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from config import BOT_TOKEN
from db import *
from texts import TEXTS
from economy import calculate_level

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

init_db()

def get_lang(user_id):
    user = get_user(user_id)
    if user:
        return user[2]
    return "ru"


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    register_user(message.from_user.id, message.from_user.username)

    lang = get_lang(message.from_user.id)

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("🌍 Язык", callback_data="language")
    )

    await message.answer(TEXTS[lang]["welcome"], reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(callback: types.CallbackQuery):

    user = get_user(callback.from_user.id)
    lang = get_lang(callback.from_user.id)

    level = calculate_level(user[6])

    text = (
        f"👤 @{user[1]}\n\n"
        f"{TEXTS[lang]['money']}: {user[3]}\n"
        f"{TEXTS[lang]['diamonds']}: {user[4]}\n"
        f"{TEXTS[lang]['level']}: {level}\n"
        f"{TEXTS[lang]['wins']}: {user[7]}"
    )

    await callback.message.answer(text)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data == "language")
async def language(callback: types.CallbackQuery):

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
    )

    lang = get_lang(callback.from_user.id)
    await callback.message.answer(TEXTS[lang]["choose_language"], reply_markup=keyboard)
    await callback.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    update_language(callback.from_user.id, lang)
    await callback.message.answer("✅ Language updated.")
    await callback.answer()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
