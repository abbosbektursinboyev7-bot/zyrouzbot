import logging
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- SOZLAMALAR ---
TOKEN = "8417752133:AAEkt8YPxSzMpaGjEFrexiiH4-DHstuDAZM"
ADMIN_ID = 6747463423  # Sizning shaxsiy ID raqamingiz

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- DATABASE QISMI ---
def init_db():
    conn = sqlite3.connect('kino_bot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY, chat_id TEXT, url TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS movies (id INTEGER PRIMARY KEY, code TEXT, name TEXT, file_id TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')  # Statistika uchun
    conn.commit()
    conn.close()

init_db()

# --- STATES ---
class AdminStates(StatesGroup):
    add_channel_id = State()
    add_channel_url = State()
    add_movie_file = State()
    add_movie_code = State()
    add_movie_name = State()
    search_movie = State()
    del_movie_code = State()  # Kino o'chirish uchun
    del_chan_id = State()     # Kanal o'chirish uchun

# --- FUNKSIYALAR ---
async def check_sub(user_id):
    conn = sqlite3.connect('kino_bot.db')
    c = conn.cursor()
    c.execute('SELECT chat_id, url FROM channels')
    channels = c.fetchall()
    conn.close()
    
    not_subbed = []
    for ch_id, url in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ['left', 'kicked']:
                not_subbed.append(url)
        except Exception:
            not_subbed.append(url)
    return not_subbed

# --- HANDLERS ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    # Foydalanuvchini bazaga saqlash
    conn = sqlite3.connect('kino_bot.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.from_user.id,))
    conn.commit()
    conn.close()

    unsubscribed = await check_sub(message.from_user.id)
    if unsubscribed:
        builder = InlineKeyboardBuilder()
        for i, url in enumerate(unsubscribed, 1):
            builder.row(types.InlineKeyboardButton(text=f"{i}-kanal", url=url))
        builder.row(types.InlineKeyboardButton(text="✅ Tekshirish", callback_data="check"))
        await message.answer("Botdan foydalanish uchun kanallarga a'zo bo'ling:", reply_markup=builder.as_markup())
    else:
        await message.answer("Xush kelibsiz! Kino kodini kiriting yoki /search tugmasini bosing.")

@dp.callback_query(F.data == "check")
async def check_callback(call: types.CallbackQuery):
    unsubscribed = await check_sub(call.from_user.id)
    if not unsubscribed:
        await call.message.edit_text("Rahmat! Endi kino kodini yuborishingiz mumkin.")
    else:
        await call.answer("Hali hamma kanallarga a'zo bo'lmadingiz!", show_alert=True)

# Kino kodini qabul qilish
@dp.message(F.text.isdigit())
async def get_movie_by_code(message: types.Message):
    unsubscribed = await check_sub(message.from_user.id)
    if unsubscribed: return await start_cmd(message)

    conn = sqlite3.connect('kino_bot.db')
    c = conn.cursor()
    c.execute('SELECT file_id, name FROM movies WHERE code=?', (message.text,))
    movies = c.fetchall()
    conn.close()

    if movies:
        for movie in movies:
            try:
                # Fayl yoki video ekanligini avtomatik aniqlash
                await message.answer_document(movie[0], caption=f"🎬 Nomi: {movie[1]}")
            except:
                await message.answer_video(movie[0], caption=f"🎬 Nomi: {movie[1]}")
    else:
        await message.answer("Kechirasiz, bu kod bilan kino topilmadi.")

# --- QIDIRUV ---
@dp.message(Command("search"))
async def search_start(message: types.Message, state: FSMContext):
    await message.answer("Kino nomini kiriting:")
    await state.set_state(AdminStates.search_movie)

@dp.message(AdminStates.search_movie)
async def search_process(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('kino_bot.db')
    c = conn.cursor()
    c.execute("SELECT code, name FROM movies WHERE name LIKE ?", (f'%{message.text}%',))
    results = c.fetchall()
    conn.close()

    if results:
        text = "Topilgan kinolar:\n"
        for code, name in results:
            text += f"🆔 {code} | 🎥 {name}\n"
        await message.answer(text + "\nKodni yuboring.")
    else:
        await message.answer("Hech narsa topilmadi.")
    await state.clear()

# --- ADMIN PANEL ---
@dp.message(Command("admin"))
async def admin_menu(message: types.Message):
    # Faqat sizning ID'ingizga ruxsat
    if message.from_user.id != ADMIN_ID:
        return 

    conn = sqlite3.connect('kino_bot.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    u_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM movies')
    m_count = c.fetchone()[0]
    conn.close()

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_chan"))
    builder.row(types.InlineKeyboardButton(text="❌ Kanal o'chirish", callback_data="del_chan"))
    builder.row(types.InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="add_mov"))
    builder.row(types.InlineKeyboardButton(text="❌ Kino o'chirish", callback_data="del_mov"))
    
    await message.answer(
        f"📊 **Statistika:**\n👤 Azolar: {u_count}\n🎬 Kinolar: {m_count}\n\nPanel:",
        reply_markup=builder.as_markup()
    )

# --- O'CHIRISH FUNKSIYALARI ---
@dp.callback_query(F.data == "del_mov")
async def del_movie_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("O'chiriladigan kino kodini yuboring:")
    await state.set_state(AdminStates.del_movie_code)

@dp.message(AdminStates.del_movie_code)
async def del_movie_finish(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('kino_bot.db')
    c = conn.cursor()
    c.execute('DELETE FROM movies WHERE code=?', (message.text,))
    conn.commit()
    conn.close()
    await message.answer("Kino o'chirildi!")
    await state.clear()

@dp.callback_query(F.data == "del_chan")
async def del_chan_start(call: types.CallbackQuery, state: FSMContext):
    conn = sqlite3.connect('kino_bot.db')
    c = conn.cursor()
    c.execute('SELECT id, url FROM channels')
    chans = c.fetchall()
    conn.close()
    
    txt = "Kanallar:\n"
    for cid, url in chans:
        txt += f"ID: {cid} | Link: {url}\n"
    await call.message.answer(txt + "\nO'chiriladigan kanal tartib raqamini (ID) yuboring:")
    await state.set_state(AdminStates.del_chan_id)

@dp.message(AdminStates.del_chan_id)
async def del_chan_finish(message: types.Message, state: FSMContext):
    conn = sqlite3.connect('kino_bot.db')
    c = conn.cursor()
    c.execute('DELETE FROM channels WHERE id=?', (message.text,))
    conn.commit()
    conn.close()
    await message.answer("Kanal o'chirildi!")
    await state.clear()

# --- QO'SHISH FUNKSIYALARI ---
@dp.callback_query(F.data == "add_chan")
async def add_ch_step1(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Kanal ID sini yuboring (masalan: -100123456):")
    await state.set_state(AdminStates.add_channel_id)

@dp.message(AdminStates.add_channel_id)
async def add_ch_step2(message: types.Message, state: FSMContext):
    await state.update_data(id=message.text)
    await message.answer("Kanal linkini yuboring:")
    await state.set_state(AdminStates.add_channel_url)

@dp.message(AdminStates.add_channel_url)
async def add_ch_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect('kino_bot.db')
    c = conn.cursor()
    c.execute('INSERT INTO channels (chat_id, url) VALUES (?,?)', (data['id'], message.text))
    conn.commit()
    conn.close()
    await message.answer("Kanal qo'shildi!")
    await state.clear()

@dp.callback_query(F.data == "add_mov")
async def add_m_step1(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Kino faylini yuboring:")
    await state.set_state(AdminStates.add_movie_file)

@dp.message(AdminStates.add_movie_file)
async def add_m_step2(message: types.Message, state: FSMContext):
    file_id = message.video.file_id if message.video else message.document.file_id
    await state.update_data(fid=file_id)
    await message.answer("Kod kiriting:")
    await state.set_state(AdminStates.add_movie_code)

@dp.message(AdminStates.add_movie_code)
async def add_m_step3(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text)
    await message.answer("Nomini kiriting:")
    await state.set_state(AdminStates.add_movie_name)

@dp.message(AdminStates.add_movie_name)
async def add_m_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect('kino_bot.db')
    c = conn.cursor()
    c.execute('INSERT INTO movies (code, name, file_id) VALUES (?,?,?)', (data['code'], message.text, data['fid']))
    conn.commit()
    conn.close()
    await message.answer(f"Kino saqlandi!")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())