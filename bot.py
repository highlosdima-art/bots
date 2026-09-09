import os
import json
from datetime import datetime, date
import telebot
from telebot import types

# ====================================================
# 1. ТВІЙ ТОКЕН (БЕРЕТЬСЯ ІЗ ЗМІННИХ СЕРЕДОВИЩА)
# ====================================================
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не знайдено! Додай змінну в Railway.")

bot = telebot.TeleBot(TOKEN)

# ====================================================
# 2. ТВІЙ TELEGRAM ID (АДМІН)
#    Отримай через @userinfobot
# ====================================================
ADMIN_ID = 123456789  # 🔴 ЗАМІНИ НА СВІЙ ID

# ====================================================
# 3. ФАЙЛ ДЛЯ ЗБЕРЕЖЕННЯ ДАНИХ
# ====================================================
DATA_FILE = 'smoke_data.json'

# ====================================================
# 4. РОБОТА З БАЗОЮ ДАНИХ (JSON)
# ====================================================

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    data = load_data()
    user_id = str(user_id)
    
    if user_id not in data:
        data[user_id] = {
            'user_info': {
                'id': user_id,
                'username': '',
                'first_name': '',
                'last_name': '',
                'registered_at': datetime.now().isoformat()
            },
            'settings': {
                'brand': 'Вінстон X Style 6',
                'pack_price': 170,
                'pack_count': 20,
                'price_per_cigarette': 8.5
            },
            'daily': {
                'count': 0,
                'spent': 0.0,
                'date': date.today().isoformat()
            },
            'total': {
                'count': 0,
                'spent': 0.0
            },
            'history': []
        }
        save_data(data)
    
    return data[user_id]

def check_reset(user_id):
    data = load_data()
    user_id = str(user_id)
    today = date.today().isoformat()
    
    if data[user_id]['daily']['date'] != today:
        data[user_id]['total']['count'] += data[user_id]['daily']['count']
        data[user_id]['total']['spent'] += data[user_id]['daily']['spent']
        data[user_id]['daily']['count'] = 0
        data[user_id]['daily']['spent'] = 0.0
        data[user_id]['daily']['date'] = today
        save_data(data)

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

# ====================================================
# 5. КОМАНДИ ДЛЯ ВСІХ КОРИСТУВАЧІВ
# ====================================================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    data = load_data()
    data[str(user_id)]['user_info']['username'] = message.from_user.username or ''
    data[str(user_id)]['user_info']['first_name'] = message.from_user.first_name or ''
    data[str(user_id)]['user_info']['last_name'] = message.from_user.last_name or ''
    save_data(data)
    
    settings = user_data['settings']
    
    text = f"""🚬 *Вітаю! Лічильник сигарет*

📊 *Твої налаштування:*
🏷️ Бренд: {settings['brand']}
💰 Ціна пачки: {settings['pack_price']} ₴
📦 Сигарет у пачці: {settings['pack_count']} шт
💵 Ціна за 1 шт: {settings['price_per_cigarette']:.2f} ₴

📌 *Команди:*
/smoke - викурити сигарету
/stats - моя статистика
/settings - налаштування

👤 Твій ID: `{user_id}`"""
    
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['smoke'])
def smoke(message):
    user_id = str(message.from_user.id)
    check_reset(user_id)
    
    data = load_data()
    price = data[user_id]['settings']['price_per_cigarette']
    brand = data[user_id]['settings']['brand']
    
    record = {
        'date': date.today().isoformat(),
        'time': datetime.now().strftime('%H:%M:%S'),
        'price': price,
        'brand': brand
    }
    data[user_id]['history'].append(record)
    data[user_id]['daily']['count'] += 1
    data[user_id]['daily']['spent'] += price
    save_data(data)
    
    response = f"""🚬 *Викурив сигарету!*

💨 {brand}
💸 Списано: *{price:.2f} ₴*
🕐 Час: {record['time']}

📊 *Сьогодні:*
🚬 Викурено: *{data[user_id]['daily']['count']}* шт
💰 Витрачено: *{data[user_id]['daily']['spent']:.2f}* ₴"""
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats(message):
    user_id = str(message.from_user.id)
    check_reset(user_id)
    
    data = load_data()
    user = data[user_id]
    settings = user['settings']
    
    text = f"""📊 *Твоя статистика*

🔹 *Бренд:* {settings['brand']}
🔹 *Ціна за 1 шт:* {settings['price_per_cigarette']:.2f} ₴

📆 *Сьогодні:*
🚬 Викурено: *{user['daily']['count']}* шт
💰 Витрачено: *{user['daily']['spent']:.2f}* ₴

📈 *За весь час:*
🚬 Всього: *{user['total']['count'] + user['daily']['count']}* шт
💰 Всього: *{user['total']['spent'] + user['daily']['spent']:.2f}* ₴

📋 *Записів в історії:* {len(user['history'])} шт"""
    
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['settings'])
def settings_menu(message):
    user_id = str(message.from_user.id)
    data = load_data()
    settings = data[user_id]['settings']
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🏷️ Бренд", callback_data="set_brand"),
        types.InlineKeyboardButton("💰 Ціна пачки", callback_data="set_price"),
        types.InlineKeyboardButton("📦 Кількість", callback_data="set_count")
    )
    
    text = f"""⚙️ *Твої налаштування*

🏷️ Бренд: *{settings['brand']}*
💰 Ціна пачки: *{settings['pack_price']}* ₴
📦 Сигарет у пачці: *{settings['pack_count']}* шт
💵 Ціна за 1 шт: *{settings['price_per_cigarette']:.2f}* ₴"""
    
    bot.reply_to(message, text, parse_mode='Markdown', reply_markup=keyboard)

# ====================================================
# 6. ОБРОБКА КНОПОК НАЛАШТУВАНЬ
# ====================================================

@bot.callback_query_handler(func=lambda call: True)
def handle_settings(call):
    user_id = str(call.from_user.id)
    
    if call.data == "set_brand":
        msg = bot.send_message(call.message.chat.id, "✏️ Напиши нову назву бренду:")
        bot.register_next_step_handler(msg, set_brand, user_id)
    
    elif call.data == "set_price":
        msg = bot.send_message(call.message.chat.id, "✏️ Введи ціну пачки (грн):")
        bot.register_next_step_handler(msg, set_pack_price, user_id)
    
    elif call.data == "set_count":
        msg = bot.send_message(call.message.chat.id, "✏️ Введи кількість сигарет у пачці:")
        bot.register_next_step_handler(msg, set_pack_count, user_id)
    
    bot.answer_callback_query(call.id)

def set_brand(message, user_id):
    data = load_data()
    data[user_id]['settings']['brand'] = message.text.strip()
    save_data(data)
    bot.reply_to(message, f"✅ Бренд змінено на *{data[user_id]['settings']['brand']}*!", parse_mode='Markdown')

def set_pack_price(message, user_id):
    try:
        price = float(message.text.replace(',', '.'))
        data = load_data()
        data[user_id]['settings']['pack_price'] = price
        data[user_id]['settings']['price_per_cigarette'] = price / data[user_id]['settings']['pack_count']
        save_data(data)
        bot.reply_to(
            message,
            f"✅ Ціну пачки змінено на *{price:.2f}* ₴\n"
            f"💰 Ціна за 1 шт: *{data[user_id]['settings']['price_per_cigarette']:.2f}* ₴",
            parse_mode='Markdown'
        )
    except:
        bot.reply_to(message, "❌ Введи коректне число")

def set_pack_count(message, user_id):
    try:
        count = int(message.text)
        data = load_data()
        data[user_id]['settings']['pack_count'] = count
        data[user_id]['settings']['price_per_cigarette'] = data[user_id]['settings']['pack_price'] / count
        save_data(data)
        bot.reply_to(
            message,
            f"✅ Кількість змінено на *{count}* шт\n"
            f"💰 Ціна за 1 шт: *{data[user_id]['settings']['price_per_cigarette']:.2f}* ₴",
            parse_mode='Markdown'
        )
    except:
        bot.reply_to(message, "❌ Введи ціле число")

# ====================================================
# 7. КОМАНДА ТІЛЬКИ ДЛЯ ТЕБЕ (АДМІНА)
# ====================================================

@bot.message_handler(commands=['getdata'])
def get_data_file(message):
    """Надсилає файл smoke_data.json (тільки для адміна)"""
    user_id = str(message.from_user.id)
    
    if not is_admin(user_id):
        bot.reply_to(message, "⛔ Доступ заборонено. Ця команда тільки для адміністратора.")
        return
    
    if not os.path.exists(DATA_FILE):
        bot.reply_to(message, "❌ Файл з даними ще не створено.")
        return
    
    try:
        with open(DATA_FILE, 'rb') as f:
            bot.send_document(
                message.chat.id,
                f,
                caption=f"📊 База даних SmokeCounter\n"
                        f"📅 Дата: {date.today().isoformat()}\n"
                        f"📁 Розмір: {os.path.getsize(DATA_FILE)} байт"
            )
    except Exception as e:
        bot.reply_to(message, f"❌ Помилка: {e}")

# ====================================================
# 8. ЗАПУСК БОТА
# ====================================================

if __name__ == '__main__':
    print("🤖 Бот запущено!")
    print(f"👑 Адмін ID: {ADMIN_ID}")
    print("📱 Знайди свого бота в Telegram і напиши /start")
    bot.polling(none_stop=True)
