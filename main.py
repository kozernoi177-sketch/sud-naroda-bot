import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

players = []
game_active = False
current_accused = None
votes = {}


@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎮 Создать игру", callback_data="create_game"))
    await message.answer("⚖️ Суд народа\n\nНажмите, чтобы создать игру.", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == "create_game")
async def create_game(callback: types.CallbackQuery):
    global players, game_active, votes
    players = []
    votes = {}
    game_active = False
    await callback.message.answer("Игра создана!\nНапишите /join чтобы присоединиться.")
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
    global current_accused, votes

    votes = {}
    current_accused = random.choice(players)

    user = await bot.get_chat(current_accused)

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔴 Казнить", callback_data="guilty"),
        InlineKeyboardButton("🟢 Оправдать", callback_data="innocent")
    )

    await bot.send_message(
        chat_id,
        f"⚖️ Игра начинается!\n\n"
        f"🔴 Обвиняемый: @{user.username if user.username else user.first_name}\n\n"
        f"У вас 30 секунд на голосование.",
        reply_markup=keyboard
    )

    await asyncio.sleep(30)
    await finish_round(chat_id)


@dp.callback_query_handler(lambda c: c.data in ["guilty", "innocent"])
async def vote_handler(callback: types.CallbackQuery):
    global votes

    if callback.from_user.id not in players:
        await callback.answer("Вы не участвуете в игре.", show_alert=True)
        return

    votes[callback.from_user.id] = callback.data
    await callback.answer("Голос принят.")


async def finish_round(chat_id):
    global game_active

    guilty_votes = list(votes.values()).count("guilty")
    innocent_votes = list(votes.values()).count("innocent")

    verdict = random.choice(["guilty", "innocent"])  # случайная истина для MVP

    result_text = f"\n📊 Голоса:\n🔴 Казнить: {guilty_votes}\n🟢 Оправдать: {innocent_votes}\n\n"

    if verdict == "guilty":
        result_text += "⚠️ Обвиняемый действительно ВИНОВЕН!"
    else:
        result_text += "❗ Обвиняемый был НЕВИНОВЕН!"

    await bot.send_message(chat_id, result_text)

    game_active = False


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
