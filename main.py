import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

players = []

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎮 Создать игру", callback_data="create_game"))
    await message.answer("⚖️ Суд народа\n\nНажмите, чтобы создать игру.", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "create_game")
async def create_game(callback: types.CallbackQuery):
    players.clear()
    await bot.send_message(callback.from_user.id, "Игра создана!\nНапишите /join чтобы присоединиться.")
    await callback.answer()

@dp.message_handler(commands=['join'])
async def join_game(message: types.Message):
    if message.from_user.id not in players:
        players.append(message.from_user.id)
        await message.answer(f"Вы присоединились! Игроков: {len(players)}")
    else:
        await message.answer("Вы уже в игре.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
