import asyncio
import requests
import random

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from decouple import config
TOKEN = config('BOT_TOKEN2')
SITE_URL = config('SITE_URL')


class Registration(StatesGroup):
    full_name = State()
    home_address = State()
    phone_contact = State()


async def cmd_start(message: types.Message, state: FSMContext):
    # Avvalo, foydalanuvchi mavjudligini tekshiramiz
    try:
        resp = requests.post(
            f"{SITE_URL}/api/bot-start/",
            json={"chat_id": str(message.from_user.id)},
            timeout=10
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("status") == "ok":
            await state.clear()
            await message.answer(
                f"Hisobingiz topildi!\n"
                f"Login: {body['username']}\n"
                f"Parol: {body['password']}\n"
                f"Iltimos, shu ma'lumotlar bilan saytda <a href='http://mas-kan.uz/maskan/login.uz'>Kirish</a>.",
                parse_mode="HTML"
            )
            return
    except Exception:
        # Agar serverda xatolik bo'lsa, ro'yxatdan o'tish jarayoniga o'tamiz
        pass

    await state.set_state(Registration.full_name)
    await message.answer("Ism Familyangizni kiriting:")


async def get_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await state.set_state(Registration.home_address)
    await message.answer("Uy manzilingizni kiriting:")


async def get_address(message: types.Message, state: FSMContext):
    await state.update_data(home_address=message.text.strip())
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await state.set_state(Registration.phone_contact)
    await message.answer("Asosiy telefon raqamingizni yuboring (Kontakt orqali):", reply_markup=kb)


async def get_contact(message: types.Message, state: FSMContext):
    if not message.contact:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer("Iltimos, kontakt orqali yuboring.", reply_markup=kb)
        return
    await state.update_data(phone_number=message.contact.phone_number)
    await finish_registration(message, state)  # <-- To'g'ridan-to'g'ri tugatish


async def finish_registration(message: types.Message, state: FSMContext):
    data = await state.get_data()
    password = str(random.randint(100000, 999999))  # 6 xonali random parol
    payload = {
        "full_name": data.get("full_name", ""),
        "home_address": data.get("home_address", ""),
        "phone_number": data.get("phone_number", ""),
        "password": password,
        "chat_id": str(message.from_user.id),
    }

    try:
        resp = requests.post(f"{SITE_URL}/api/bot-register/", json=payload, timeout=10)
        resp.raise_for_status()
        body = resp.json()
        if body.get("status") == "ok":
            await message.answer(
                f"Ro'yxatdan o'tdingiz!\nLogin: {body['username']}\nParol: {body['password']}\nIltimos, saytda ushbu ma'lumotlar bilan kiring."
            )
            # Quyidagi kod yangi
            ADMIN_CHAT_ID = config('CHAT_ID')
            user_info = (
                f"Yangi foydalanuvchi ro'yxatdan o'tdi:\n"
                f"Ism: {data.get('full_name', '')}\n"
                f"Manzil: {data.get('home_address', '')}\n"
                f"Telefon: {data.get('phone_number', '')}\n"
                f"Chat ID: {message.from_user.id}"
                
            )
            bot = message.bot
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=user_info)
        else:
            await message.answer(f"Xatolik: {body.get('message', 'nomaʼlum')}")
    except Exception:
        await message.answer("Server bilan aloqa xatosi. Keyinroq urinib ko'ring.")

    await state.clear()


async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(get_full_name, Registration.full_name)
    dp.message.register(get_address, Registration.home_address)
    dp.message.register(get_contact, Registration.phone_contact)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
