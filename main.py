import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

players = []

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Создать игру", callback_data="create_game")]
    ])
    await message.answer("⚖️ Суд народа\n\nНажмите, чтобы создать игру.", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "create_game")
async def create_game(callback: types.CallbackQuery):
    players.clear()
    await callback.message.answer("Игра создана!\nНажмите /join чтобы присоединиться.")
    await callback.answer()

@dp.message(Command("join"))
async def join_game(message: types.Message):
    if message.from_user.id not in players:
        players.append(message.from_user.id)
        await message.answer(f"Вы присоединились! Игроков: {len(players)}")
    else:
        await message.answer("Вы уже в игре.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
