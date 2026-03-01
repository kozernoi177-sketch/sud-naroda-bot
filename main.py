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
truth = None
detective = None
detective_used = False


@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎮 Создать игру", callback_data="create_game"))
    await message.answer("⚖️ Суд народа 2.0\n\nНажмите, чтобы создать игру.", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == "create_game")
async def create_game(callback: types.CallbackQuery):
    global players, game_active, votes, round_number, scores, detective, detective_used
    players = []
    votes = {}
    scores = {}
    round_number = 0
    detective = None
    detective_used = False
    game_active = False
    await callback.message.answer("Игра создана!\nНапишите /join чтобы присоединиться.")
    await callback.answer()


@dp.message_handler(commands=['join'])
async def join_game(message: types.Message):
    global game_active, detective

    if game_active:
        await message.answer("Игра уже идёт.")
        return

    if message.from_user.id not in players:
        players.append(message.from_user.id)
        scores[message.from_user.id] = 0
        await message.answer(f"Вы присоединились! Игроков: {len(players)}")

        if len(players) == 2:  # для теста
            detective = random.choice(players)
            await bot.send_message(detective, "🕵 Вы — Детектив! Напишите /check в раунде, чтобы узнать истину (1 раз).")
            game_active = True
            await start_round(message.chat.id)

    else:
        await message.answer("Вы уже в игре.")


async def start_round(chat_id):
    global current_accused, votes, round_number, truth

    votes = {}
    round_number += 1
    current_accused = random.choice(players)
    truth = random.choice(["guilty", "innocent"])

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


@dp.message_handler(commands=['check'])
async def detective_check(message: types.Message):
    global detective_used

    if message.from_user.id != detective:
        return

    if detective_used:
        await message.answer("Вы уже использовали проверку.")
        return

    detective_used = True

    if truth == "guilty":
        await message.answer("🔎 Истина: Обвиняемый ВИНОВЕН.")
    else:
        await message.answer("🔎 Истина: Обвиняемый НЕВИНОВЕН.")


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
        public_verdict = "guilty"
    else:
        public_verdict = "innocent"

    result_text = f"\n📊 Голоса:\n🔴 {guilty_votes}\n🟢 {innocent_votes}\n\n"

    if public_verdict == truth:
        result_text += "✅ Толпа приняла ПРАВИЛЬНОЕ решение!\n"
        for user_id in votes:
            if votes[user_id] == truth:
                scores[user_id] += 1
    else:
        result_text += "❌ Толпа ОШИБЛАСЬ!\n"

    if truth == "guilty":
        result_text += "⚠️ Истина: Обвиняемый был ВИНОВЕН."
    else:
        result_text += "🟢 Истина: Обвиняемый был НЕВИНОВЕН."

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
