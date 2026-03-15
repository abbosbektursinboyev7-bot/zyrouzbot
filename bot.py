import telebot
import firebase_admin
from firebase_admin import credentials, db
from telebot import types

# 1. Firebase va Bot sozlamalari
TOKEN = "SIZNING_BOT_TOKENINGIZ"
ADMIN = 123456789 # Admin ID raqamingizni kiriting

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://kinochi-zyro-bot-default-rtdb.firebaseio.com/'
})

bot = telebot.TeleBot(TOKEN)

# Baza yo'llari
movies = db.reference("movies")
categories = db.reference("categories")
users = db.reference("users")

# START komandasi
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    # Foydalanuvchini bazaga qo'shish
    users.child(user_id).set({
        "username": message.from_user.username,
        "name": message.from_user.first_name
    })
    bot.send_message(message.chat.id, "🎬 Kino botga xush kelibsiz!\n\nKino nomi yoki kodini yuboring.")

# ADMIN PANEL
@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.id == ADMIN:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Kino qo'shish", "❌ Kino o'chirish")
        markup.add("📂 Kategoriya qo'shish", "🗑 Kategoriya o'chirish")
        markup.add("📃 Kinolar ro'yxati", "📊 Statistika")
        bot.send_message(message.chat.id, "⚙️ Admin panelga xush kelibsiz", reply_markup=markup)

# KINO QO‘SHISH
@bot.message_handler(func=lambda m: m.text == "➕ Kino qo'shish")
def add_movie(message):
    if message.from_user.id == ADMIN:
        msg = bot.send_message(message.chat.id, "Format: code|name|desc|video_link|category")
        bot.register_next_step_handler(msg, save_movie)

def save_movie(message):
    try:
        data = message.text.split("|")
        movies.child(data[0]).set({
            "name": data[1],
            "desc": data[2],
            "video": data[3],
            "category": data[4]
        })
        bot.send_message(message.chat.id, "✅ Kino muvaffaqiyatli qo‘shildi!")
    except:
        bot.send_message(message.chat.id, "❌ Xatolik! Formani to'g'ri kiriting.")

# KINO QIDIRISH (Universal)
@bot.message_handler(func=lambda message: True)
def search(message):
    data = movies.get()
    if data:
        for code, item in data.items():
            if message.text.lower() == str(code).lower() or message.text.lower() in item["name"].lower():
                text = f"🎬 *{item['name']}*\n\n📝 {item['desc']}\n📂 Kategoriya: {item['category']}"
                bot.send_message(message.chat.id, text, parse_mode="Markdown")
                bot.send_message(message.chat.id, item["video"])
                return
    bot.send_message(message.chat.id, "❌ Kino topilmadi.")

print("Bot ishga tushdi...")
bot.infinity_polling()