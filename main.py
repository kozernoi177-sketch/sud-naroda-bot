import os
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

players = []
game_active = False


@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎮 Создать игру", callback_data="create_game"))
    await message.answer("⚖️ Суд народа\n\nНажмите, чтобы создать игру.", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == "create_game")
async def create_game(callback: types.CallbackQuery):
    global players, game_active
    players = []
    game_active = False
    await bot.send_message(callback.from_user.id, "Игра создана!\nНапишите /join чтобы присоединиться.")
    await callback.answer()


@dp.message_handler(commands=['join'])
async def join_game(message: types.Message):
    global game_active

    if game_active:
        await message.answer("Игра уже идёт.")
        return

    if message.from_user.id not in players:
        players.append(message.from_user.id)
        await message.answer(f"Вы присоединились! Игроков: {len(players)}")

        if len(players) == 6:
            game_active = True
            await start_round(message.chat.id)

    else:
        await message.answer("Вы уже в игре.")


async def start_round(chat_id):
    accused = random.choice(players)
    user = await bot.get_chat(accused)

    await bot.send_message(
        chat_id,
        f"⚖️ Игра начинается!\n\n"
        f"🔴 Обвиняемый: @{user.username if user.username else user.first_name}\n\n"
        f"Обсуждение 60 секунд..."
    )


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
