import telebot
from telebot import types
import firebase_admin
from firebase_admin import credentials, db

# ------------------- CONFIG -------------------
TOKEN = "8727652023:AAG6teald5OIAzgGgnm5idD6eNjM0A66owU"
ADMIN_ID = 6747463423  # Admin Telegram ID
MANDATORY_CHANNELS = ["@Qorqinchli_Dahshatliy_Kinolar", "@zyrouz"]
# ---------------------------------------------

bot = telebot.TeleBot(TOKEN)

# ---------------- FIREBASE -------------------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://kino-uz-bot-default-rtdb.firebaseio.com/'
})

movies_ref = db.reference("movies")
users_ref = db.reference("users")
channels_ref = db.reference("mandatory_channels")
# ---------------------------------------------

# ---------- HELP FUNCTION -------------------
HELP_TEXT = """
📖 Botdan foydalanish yo‘riqnomasi

/start - Botni ishga tushirish
/search - Kino yoki serial qidirish
/top - Eng ommabop kinolar
/genre - Janrlar bo‘yicha tanlash
/help - Botdan foydalanish yo‘riqnomasi
/feedback - Admin bilan bog‘lanish

🎬 Kino topish uchun:
1️⃣ Qidirish tugmasini bosing  
2️⃣ Kino nomini yozing  
3️⃣ Bot sizga kinoni chiqarib beradi
"""
# ---------------------------------------------

# ---------- START COMMAND -------------------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or ""

    # Foydalanuvchi Firebase ga qo‘shish
    users_ref.child(user_id).set({"username": username})

    # Majburiy kanal tekshirish
    not_subscribed = []
    for ch in MANDATORY_CHANNELS:
        try:
            member = bot.get_chat_member(ch, int(user_id))
            if member.status in ["left", "kicked"]:
                not_subscribed.append(ch)
        except:
            not_subscribed.append(ch)

    if not_subscribed:
        text = "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:\n"
        for ch in not_subscribed:
            text += f"👉 {ch}\n"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("✅ Tekshirish"))
        bot.send_message(user_id, text, reply_markup=markup)
    else:
        send_main_menu(message)

def send_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔎 Qidirish","🔥 Top kinolar")
    markup.add("🎭 Janrlar","ℹ️ Yordam")
    markup.add("📩 Feedback")
    bot.send_message(message.from_user.id,"🎬 Zyro.uz kino botiga xush kelibsiz\nKerakli bo‘limni tanlang",reply_markup=markup)
# ---------------------------------------------

# ---------- HELP COMMAND --------------------
@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(message.chat.id, HELP_TEXT)
# ---------------------------------------------

# ---------- TEXT HANDLER --------------------
@bot.message_handler(func=lambda message: True)
def text_handler(message):
    text = message.text
    user_id = str(message.from_user.id)

    # Tekshirish tugmasi
    if text == "✅ Tekshirish":
        start(message)
        return

    # Qidiruv
    if text == "🔎 Qidirish":
        msg = bot.send_message(user_id, "🔎 Kino nomini yozing")
        bot.register_next_step_handler(msg, search_movie)
        return
    
    # Janrlar
    if text == "🎭 Janrlar":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        genres = ["Drama","Komediya","Horror","Jangari","Fantasy","Romantik"]
        for g in genres:
            markup.add(g)
        bot.send_message(user_id,"🎬 Janr tanlang",reply_markup=markup)
        return

    # Top kinolar
    if text == "🔥 Top kinolar":
        movies = movies_ref.order_by_key().limit_to_last(10).get()
        if movies:
            sorted_movies = sorted(movies.items(), key=lambda x: int(x[0]), reverse=True)
            msg = "🔥 Eng yangi kinolar:\n"
            for i, (_, m) in enumerate(sorted_movies, 1):
                msg += f"{i}️⃣ {m['name']}\n"
            bot.send_message(user_id, msg)
        else:
            bot.send_message(user_id,"Hozircha kino yo‘q")
        return

    # Yordam
    if text == "ℹ️ Yordam":
        bot.send_message(user_id, HELP_TEXT)
        return

    # Feedback
    if text == "📩 Feedback":
        bot.send_message(user_id, "Admin bilan bog‘lanish: @admin_username")
        return

    # Janr bo‘yicha kinolar
    movies = movies_ref.get()
    filtered = [m['name'] for m in movies.values()] if movies else []
    genre_filtered = []
    if movies:
        for m in movies.values():
            if m['genre'].lower() == text.lower():
                genre_filtered.append(m['name'])
    if genre_filtered:
        msg = f"🎬 {text} janridagi kinolar:\n"
        for i, m in enumerate(genre_filtered, 1):
            msg += f"{i}️⃣ {m}\n"
        bot.send_message(user_id,msg)
        return

    # Kino kodi orqali
    movies = movies_ref.get()
    found = None
    if movies:
        for m in movies.values():
            if m['code'] == text:
                found = m
                break
    if found:
        # Kanal tekshirish
        not_subscribed = []
        for ch in MANDATORY_CHANNELS:
            try:
                member = bot.get_chat_member(ch, int(user_id))
                if member.status in ["left","kicked"]:
                    not_subscribed.append(ch)
            except:
                not_subscribed.append(ch)
        if not_subscribed:
            bot.send_message(user_id,"❌ Avval kanalga obuna bo‘ling")
            return

        msg = f"🎬 {found['name']}\n📅 {found['year']}\n🎭 Janr: {found['genre']}\n\n▶️ Yuklab olish: {found['video_link']}"
        bot.send_message(user_id,msg)
        return

    # Admin panel
    if int(user_id) == ADMIN_ID and text == "👑 Admin panel":
        admin_panel(user_id)
        return

def search_movie(message):
    query = message.text.lower()
    movies = movies_ref.get()
    results = []
    if movies:
        for m in movies.values():
            if query in m['name'].lower():
                results.append(m['name'])
    if results:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for r in results:
            markup.add(r)
        bot.send_message(message.from_user.id,"Natijalar:",reply_markup=markup)
    else:
        bot.send_message(message.from_user.id,"Kino topilmadi")
# ---------------------------------------------

# ---------- ADMIN PANEL ---------------------
def admin_panel(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Kino qo‘shish","📊 Statistika")
    markup.add("📢 Majburiy kanal","🔥 Top kinolar")
    markup.add("📁 Janr qo‘shish")
    bot.send_message(user_id,"👑 Admin panel",reply_markup=markup)
# ---------------------------------------------

bot.polling(none_stop=True)
