import telebot
from telebot import types
import json
import os
from datetime import datetime, date
import threading
import time

# ТВІЙ ТОКЕН ВІД BOTFATHER
TOKEN = '8852614151:AAEUIuVXhad6kpf4-meANBbS_n9D5cQFjk0'

bot = telebot.TeleBot(TOKEN)

# Файл для збереження даних
DATA_FILE = 'smoke_data.json'

# Дефолтні налаштування
DEFAULT_SETTINGS = {
    'brand': 'Вінстон X Style 6',
    'pack_price': 170,
    'pack_count': 20,
    'price_per_cigarette': 8.5
}

def load_data():
    """Завантажує дані з файлу"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    """Зберігає дані у файл"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    """Отримує дані користувача"""
    data = load_data()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            'settings': DEFAULT_SETTINGS.copy(),
            'daily': {
                'count': 0,
                'spent': 0.0,
                'date': date.today().isoformat()
            },
            'total': {
                'count': 0,
                'spent': 0.0
            }
        }
        save_data(data)
    return data[user_id]

def update_user_data(user_id, updates):
    """Оновлює дані користувача"""
    data = load_data()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            'settings': DEFAULT_SETTINGS.copy(),
            'daily': {'count': 0, 'spent': 0.0, 'date': date.today().isoformat()},
            'total': {'count': 0, 'spent': 0.0}
        }
    
    # Оновлюємо
    for key, value in updates.items():
        if isinstance(value, dict):
            if key in data[user_id]:
                data[user_id][key].update(value)
            else:
                data[user_id][key] = value
        else:
            data[user_id][key] = value
    
    save_data(data)

def check_reset(user_id):
    """Перевіряє чи потрібно скинути денну статистику"""
    user_data = get_user_data(user_id)
    today = date.today().isoformat()
    
    if user_data['daily']['date'] != today:
        # Зберігаємо денну статистику в загальну
        user_data['total']['count'] += user_data['daily']['count']
        user_data['total']['spent'] += user_data['daily']['spent']
        
        # Скидаємо денну
        user_data['daily']['count'] = 0
        user_data['daily']['spent'] = 0.0
        user_data['daily']['date'] = today
        
        update_user_data(user_id, user_data)
        return True
    return False

# ---- КОМАНДИ БОТА ----

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    settings = user_data['settings']
    
    welcome_text = f"""🚬 *Вітаю в SmokeCounterBot!*

Я допоможу тобі рахувати витрати на сигарети.

📊 *Поточні налаштування:*
🏷️ Бренд: {settings['brand']}
💰 Ціна пачки: {settings['pack_price']} ₴
📦 Сигарет у пачці: {settings['pack_count']} шт
💵 Ціна за 1 шт: {settings['price_per_cigarette']:.2f} ₴

📌 *Команди:*
🚬 `/smoke` - викурити сигарету (списати гроші)
📊 `/stats` - показати статистику
⚙️ `/settings` - налаштувати ціну та бренд
🔄 `/reset` - скинути денну статистику

Спробуй натиснути /smoke прямо зараз!"""

    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['smoke'])
def smoke(message):
    user_id = message.from_user.id
    
    # Перевіряємо скидання
    check_reset(user_id)
    
    user_data = get_user_data(user_id)
    price = user_data['settings']['price_per_cigarette']
    brand = user_data['settings']['brand']
    
    # Додаємо сигарету
    user_data['daily']['count'] += 1
    user_data['daily']['spent'] += price
    
    update_user_data(user_id, user_data)
    
    # Відповідь з анімацією
    response = f"""🚬 *Викурив сигарету!*

💨 {brand}
💸 Списано: *{price:.2f} ₴*

📊 *Сьогодні:*
🚬 Викурено: *{user_data['daily']['count']}* шт
💰 Витрачено: *{user_data['daily']['spent']:.2f}* ₴

💪 Так тримати! (або не дуже 😅)"""
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats(message):
    user_id = message.from_user.id
    check_reset(user_id)
    
    user_data = get_user_data(user_id)
    settings = user_data['settings']
    
    stats_text = f"""📊 *Твоя статистика*

🔹 *Бренд:* {settings['brand']}
🔹 *Ціна за 1 шт:* {settings['price_per_cigarette']:.2f} ₴

📆 *Сьогодні:*
🚬 Викурено: *{user_data['daily']['count']}* шт
💰 Витрачено: *{user_data['daily']['spent']:.2f}* ₴

📈 *За весь час:*
🚬 Всього викурено: *{user_data['total']['count']}* шт
💰 Всього витрачено: *{user_data['total']['spent']:.2f}* ₴

💡 *Якщо не палити сьогодні:*
💵 Економія: *{settings['price_per_cigarette'] * 10:.2f}* ₴ (за 10 сигарет)"""

    bot.reply_to(message, stats_text, parse_mode='Markdown')

@bot.message_handler(commands=['settings'])
def settings_menu(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    settings = user_data['settings']
    
    # Створюємо клавіатуру
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    btn_brand = types.InlineKeyboardButton("🏷️ Бренд", callback_data="set_brand")
    btn_price = types.InlineKeyboardButton("💰 Ціна пачки", callback_data="set_pack_price")
    btn_count = types.InlineKeyboardButton("📦 Кількість в пачці", callback_data="set_pack_count")
    btn_back = types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
    
    keyboard.add(btn_brand, btn_price, btn_count, btn_back)
    
    settings_text = f"""⚙️ *Поточні налаштування:*

🏷️ Бренд: *{settings['brand']}*
💰 Ціна пачки: *{settings['pack_price']}* ₴
📦 Сигарет у пачці: *{settings['pack_count']}* шт
💵 Ціна за 1 шт: *{settings['price_per_cigarette']:.2f}* ₴

*Вибери, що змінити:*"""

    bot.reply_to(message, settings_text, parse_mode='Markdown', reply_markup=keyboard)

# ---- ОБРОБКА КНОПОК (налаштування) ----

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    user_data = get_user_data(user_id)
    
    if call.data == "back_to_menu":
        bot.edit_message_text(
            "🔙 Повернувся в головне меню.\nВикористовуй команди: /smoke, /stats, /settings",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id)
        return
    
    elif call.data == "set_brand":
        msg = bot.send_message(call.message.chat.id, "✏️ Напиши нову назву бренду:")
        bot.register_next_step_handler(msg, set_brand)
        bot.answer_callback_query(call.id)
    
    elif call.data == "set_pack_price":
        msg = bot.send_message(call.message.chat.id, "✏️ Введи нову ціну пачки (в грн):")
        bot.register_next_step_handler(msg, set_pack_price)
        bot.answer_callback_query(call.id)
    
    elif call.data == "set_pack_count":
        msg = bot.send_message(call.message.chat.id, "✏️ Введи кількість сигарет у пачці:")
        bot.register_next_step_handler(msg, set_pack_count)
        bot.answer_callback_query(call.id)

def set_brand(message):
    user_id = message.from_user.id
    brand = message.text.strip()
    
    user_data = get_user_data(user_id)
    user_data['settings']['brand'] = brand
    update_user_data(user_id, user_data)
    
    bot.reply_to(message, f"✅ Бренд змінено на *{brand}*!", parse_mode='Markdown')

def set_pack_price(message):
    user_id = message.from_user.id
    try:
        price = float(message.text.replace(',', '.'))
        if price <= 0:
            raise ValueError
        
        user_data = get_user_data(user_id)
        user_data['settings']['pack_price'] = price
        user_data['settings']['price_per_cigarette'] = price / user_data['settings']['pack_count']
        update_user_data(user_id, user_data)
        
        bot.reply_to(
            message,
            f"✅ Ціну пачки змінено на *{price:.2f}* ₴\n"
            f"💰 Ціна за 1 шт: *{user_data['settings']['price_per_cigarette']:.2f}* ₴",
            parse_mode='Markdown'
        )
    except:
        bot.reply_to(message, "❌ Введи коректне число (наприклад: 170)")

def set_pack_count(message):
    user_id = message.from_user.id
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError
        
        user_data = get_user_data(user_id)
        user_data['settings']['pack_count'] = count
        user_data['settings']['price_per_cigarette'] = user_data['settings']['pack_price'] / count
        update_user_data(user_id, user_data)
        
        bot.reply_to(
            message,
            f"✅ Кількість змінено на *{count}* шт\n"
            f"💰 Ціна за 1 шт: *{user_data['settings']['price_per_cigarette']:.2f}* ₴",
            parse_mode='Markdown'
        )
    except:
        bot.reply_to(message, "❌ Введи ціле число (наприклад: 20)")

@bot.message_handler(commands=['reset'])
def reset(message):
    user_id = message.from_user.id
    keyboard = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton("✅ Так, скинути", callback_data="confirm_reset")
    btn_no = types.InlineKeyboardButton("❌ Ні", callback_data="cancel_reset")
    keyboard.add(btn_yes, btn_no)
    
    bot.reply_to(
        message,
        "⚠️ *Точно скинути денну статистику?*\n"
        "Денна статистика переміститься в загальну, а сьогоднішня обнулиться.",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_reset", "cancel_reset"])
def handle_reset(call):
    user_id = call.from_user.id
    
    if call.data == "confirm_reset":
        user_data = get_user_data(user_id)
        user_data['total']['count'] += user_data['daily']['count']
        user_data['total']['spent'] += user_data['daily']['spent']
        user_data['daily']['count'] = 0
        user_data['daily']['spent'] = 0.0
        user_data['daily']['date'] = date.today().isoformat()
        update_user_data(user_id, user_data)
        
        bot.edit_message_text(
            "✅ Денну статистику скинуто!",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.edit_message_text(
            "❌ Скидання скасовано.",
            call.message.chat.id,
            call.message.message_id
        )
    
    bot.answer_callback_query(call.id)

# ---- ЗАПУСК БОТА ----

if __name__ == '__main__':
    print("🤖 Бот запущено!")
    print("📱 Знайди свого бота в Telegram і напиши /start")
    bot.polling(none_stop=True)
