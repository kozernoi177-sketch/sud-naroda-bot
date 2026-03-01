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
round_number = 0
max_rounds = 3
scores = {}


@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎮 Создать игру", callback_data="create_game"))
    await message.answer("⚖️ Суд народа\n\nНажмите, чтобы создать игру.", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == "create_game")
async def create_game(callback: types.CallbackQuery):
    global players, game_active, votes, round_number, scores
    players = []
    votes = {}
    scores = {}
    round_number = 0
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
        scores[message.from_user.id] = 0
        await message.answer(f"Вы присоединились! Игроков: {len(players)}")

        if len(players) == 2:  # для теста
            game_active = True
            await start_round(message.chat.id)

    else:
        await message.answer("Вы уже в игре.")


async def start_round(chat_id):
    global current_accused, votes, round_number

    votes = {}
    round_number += 1
    current_accused = random.choice(players)

    user = await bot.get_chat(current_accused)

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔴 Казнить", callback_data="guilty"),
        InlineKeyboardButton("🟢 Оправдать", callback_data="innocent")
    )

    await bot.send_message(
        chat_id,
        f"⚖️ Раунд {round_number}/{max_rounds}\n\n"
        f"🔴 Обвиняемый: @{user.username if user.username else user.first_name}\n\n"
        f"Голосование 20 секунд.",
        reply_markup=keyboard
    )

    await asyncio.sleep(20)
    await finish_round(chat_id)


@dp.callback_query_handler(lambda c: c.data in ["guilty", "innocent"])
async def vote_handler(callback: types.CallbackQuery):
    global votes

    if callback.from_user.id not in players:
        await callback.answer("Вы не участвуете.", show_alert=True)
        return

    if callback.from_user.id == current_accused:
        await callback.answer("Обвиняемый не может голосовать!", show_alert=True)
        return

    if callback.from_user.id in votes:
        await callback.answer("Вы уже проголосовали!", show_alert=True)
        return

    votes[callback.from_user.id] = callback.data
    await callback.answer("Голос принят.")


async def finish_round(chat_id):
    global game_active

    guilty_votes = list(votes.values()).count("guilty")
    innocent_votes = list(votes.values()).count("innocent")

    if guilty_votes > innocent_votes:
        verdict = "guilty"
    else:
        verdict = "innocent"

    if verdict == "guilty":
        for user_id in votes:
            if votes[user_id] == "guilty":
                scores[user_id] += 1
        result_text = "⚠️ Обвиняемый казнён!"
    else:
        for user_id in votes:
            if votes[user_id] == "innocent":
                scores[user_id] += 1
        result_text = "🟢 Обвиняемый оправдан!"

    result_text += f"\n\n📊 Голоса:\n🔴 {guilty_votes}\n🟢 {innocent_votes}"

    await bot.send_message(chat_id, result_text)

    if round_number < max_rounds:
        await asyncio.sleep(3)
        await start_round(chat_id)
    else:
        await end_game(chat_id)


async def end_game(chat_id):
    global game_active

    winner = max(scores, key=scores.get)
    user = await bot.get_chat(winner)

    await bot.send_message(
        chat_id,
        f"🏆 Игра окончена!\n\n"
        f"Победитель: @{user.username if user.username else user.first_name}\n"
        f"Очков: {scores[winner]}"
    )

    game_active = False


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
