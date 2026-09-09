import os
import json
from datetime import datetime, date, timedelta, timezone
import telebot
from telebot import types
import io
import csv

# ====================================================
# 1. КОНФІГУРАЦІЯ
# ====================================================
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не знайдено!")

bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 1081116211  # ТВІЙ ID

# Часовий пояс Київ
KYIV_TZ = timezone(timedelta(hours=3))

def get_kyiv_time():
    return datetime.now(KYIV_TZ)

def get_kyiv_date():
    return get_kyiv_time().date()

# ====================================================
# 2. РОБОТА З ДАНИМИ
# ====================================================
DATA_FILE = 'smoke_data.json'

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
                'registered_at': get_kyiv_time().isoformat()
            },
            'products': {},
            'active_product': None,
            'daily': {
                'count': 0,
                'spent': 0.0,
                'date': get_kyiv_date().isoformat()
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
    today = get_kyiv_date().isoformat()
    
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
# 3. ГОЛОВНЕ МЕНЮ (ДЛЯ ВСІХ КОРИСТУВАЧІВ)
# ====================================================

def main_menu(user_id):
    """Головне меню — бачать всі користувачі"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    data = load_data()
    user_data = data.get(str(user_id), {})
    has_active = user_data.get('active_product') is not None
    has_products = len(user_data.get('products', {})) > 0
    
    # Рядок 1: Головна дія
    if has_active:
        keyboard.add(types.KeyboardButton("🚬 Покурив!"))
    else:
        keyboard.add(types.KeyboardButton("⚠️ Обери продукт"))
    
    # Рядок 2: Основні функції
    keyboard.add(
        types.KeyboardButton("📊 Моя статистика"),
        types.KeyboardButton("📦 Мої продукти")
    )
    
    # Рядок 3: Керування продуктами
    keyboard.add(
        types.KeyboardButton("➕ Новий продукт"),
        types.KeyboardButton("🔄 Змінити продукт")
    )
    
    # Рядок 4: Додатково (тільки для адміна)
    if is_admin(user_id):
        keyboard.add(types.KeyboardButton("⚙️ Адмін-панель"))
    
    return keyboard

# ====================================================
# 4. СТАРТ
# ====================================================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    get_user_data(user_id)
    
    text = f"""🚀 *Вітаю в SmokeTracker!*

📌 *Почни з цих кроків:*

1️⃣ Додай свій продукт через «➕ Новий продукт»
2️⃣ Обери його через «🔄 Змінити продукт»
3️⃣ Натискай «🚬 Покурив!» коли куриш

📊 *Всі дані зберігаються автоматично*

🕐 Київський час: {get_kyiv_time().strftime('%H:%M:%S')}

💡 *Порада:* Додай всі свої продукти (сигарети, кальян, айкос) і перемикайся між ними!"""
    
    bot.reply_to(
        message,
        text,
        parse_mode='Markdown',
        reply_markup=main_menu(user_id)
    )

# ====================================================
# 5. КНОПКА "ПОКУРИВ!"
# ====================================================

@bot.message_handler(func=lambda message: message.text == "🚬 Покурив!")
def smoke_button(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if data[user_id]['active_product'] is None:
        bot.reply_to(
            message,
            "⚠️ *Спочатку обери продукт!*\n\n"
            "Натисни «🔄 Змінити продукт» та обери що куриш.",
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
        return
    
    # Вибираємо час
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        types.InlineKeyboardButton("🕐 Зараз", callback_data="smoke_now"),
        types.InlineKeyboardButton("⬅️ -1 год", callback_data="smoke_minus_1"),
        types.InlineKeyboardButton("➡️ +1 год", callback_data="smoke_plus_1"),
        types.InlineKeyboardButton("⏪ -30 хв", callback_data="smoke_minus_30"),
        types.InlineKeyboardButton("⏩ +30 хв", callback_data="smoke_plus_30"),
        types.InlineKeyboardButton("✏️ Свій час", callback_data="smoke_custom")
    )
    
    prod = data[user_id]['products'][data[user_id]['active_product']]
    emoji = {
        'cigarettes': '🚬', 'hookah': '💨', 'snus': '👃',
        'iqos': '🔥', 'vape': '💧'
    }.get(prod['type'], '📦')
    
    bot.reply_to(
        message,
        f"{emoji} *{prod['name']}*\n"
        f"💵 {prod['price_per_unit']:.2f} ₴\n\n"
        f"🕐 *Коли це було?*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('smoke_'))
def handle_smoke_time(call):
    user_id = str(call.from_user.id)
    now = get_kyiv_time()
    selected_time = now
    
    if call.data == "smoke_now":
        selected_time = now
    elif call.data == "smoke_minus_1":
        selected_time = now - timedelta(hours=1)
    elif call.data == "smoke_plus_1":
        selected_time = now + timedelta(hours=1)
    elif call.data == "smoke_minus_30":
        selected_time = now - timedelta(minutes=30)
    elif call.data == "smoke_plus_30":
        selected_time = now + timedelta(minutes=30)
    elif call.data == "smoke_custom":
        msg = bot.send_message(
            call.message.chat.id,
            "✏️ Введи час у форматі `ГГ:ХХ`\n"
            "Наприклад: `15:19`\n\n"
            "_24-годинний формат_",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, process_custom_time)
        bot.answer_callback_query(call.id)
        return
    
    process_smoke(call.message, user_id, selected_time)
    bot.answer_callback_query(call.id)

def process_custom_time(message):
    user_id = str(message.from_user.id)
    try:
        time_str = message.text.strip()
        hour, minute = map(int, time_str.split(':'))
        
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        
        now = get_kyiv_time()
        selected_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if selected_time > now:
            selected_time = selected_time - timedelta(days=1)
        
        process_smoke(message, user_id, selected_time)
        
    except:
        bot.reply_to(
            message,
            "❌ Неправильний формат. Використовуй `ГГ:ХХ`",
            parse_mode='Markdown'
        )

def process_smoke(message, user_id, smoke_time):
    check_reset(user_id)
    
    data = load_data()
    prod_id = data[user_id]['active_product']
    prod = data[user_id]['products'][prod_id]
    
    record = {
        'date': smoke_time.date().isoformat(),
        'time': smoke_time.strftime('%H:%M:%S'),
        'timestamp': smoke_time.isoformat(),
        'product_id': prod_id,
        'product_type': prod['type'],
        'product_name': prod['name'],
        'price': prod['price_per_unit']
    }
    data[user_id]['history'].append(record)
    data[user_id]['daily']['count'] += 1
    data[user_id]['daily']['spent'] += prod['price_per_unit']
    save_data(data)
    
    emoji = {
        'cigarettes': '🚬', 'hookah': '💨', 'snus': '👃',
        'iqos': '🔥', 'vape': '💧'
    }.get(prod['type'], '📦')
    
    response = f"""{emoji} *{prod['name']}*

💸 *{prod['price_per_unit']:.2f} ₴*
🕐 {smoke_time.strftime('%H:%M')}

📊 *Сьогодні:*
🚬 {data[user_id]['daily']['count']} шт
💰 {data[user_id]['daily']['spent']:.2f} ₴"""
    
    bot.reply_to(
        message,
        response,
        parse_mode='Markdown',
        reply_markup=main_menu(user_id)
    )

# ====================================================
# 6. МОЯ СТАТИСТИКА
# ====================================================

@bot.message_handler(func=lambda message: message.text == "📊 Моя статистика")
def stats_button(message):
    user_id = str(message.from_user.id)
    check_reset(user_id)
    
    data = load_data()
    user = data[user_id]
    
    # Статистика по продуктах
    product_stats = {}
    for record in user['history']:
        name = record['product_name']
        if name not in product_stats:
            product_stats[name] = {'count': 0, 'spent': 0}
        product_stats[name]['count'] += 1
        product_stats[name]['spent'] += record['price']
    
    text = f"""📊 *Твоя статистика*

📆 *Сьогодні:*
🚬 {user['daily']['count']} шт
💰 {user['daily']['spent']:.2f} ₴

📈 *За весь час:*
🚬 {user['total']['count'] + user['daily']['count']} шт
💰 {user['total']['spent'] + user['daily']['spent']:.2f} ₴

📋 *По продуктах:*"""
    
    if product_stats:
        for name, stats in product_stats.items():
            text += f"\n   • {name}: {stats['count']} шт ({stats['spent']:.2f} ₴)"
    else:
        text += "\n   • Немає записів"
    
    bot.reply_to(
        message,
        text,
        parse_mode='Markdown',
        reply_markup=main_menu(user_id)
    )

# ====================================================
# 7. МОЇ ПРОДУКТИ
# ====================================================

@bot.message_handler(func=lambda message: message.text == "📦 Мої продукти")
def my_products(message):
    user_id = str(message.from_user.id)
    data = load_data()
    products = data[user_id]['products']
    
    if not products:
        bot.reply_to(
            message,
            "📭 У тебе ще немає продуктів.\n\n"
            "Натисни «➕ Новий продукт» щоб додати.",
            reply_markup=main_menu(user_id)
        )
        return
    
    active = data[user_id]['active_product']
    text = "📦 *Твої продукти:*\n\n"
    
    for prod_id, prod in products.items():
        emoji = {
            'cigarettes': '🚬', 'hookah': '💨', 'snus': '👃',
            'iqos': '🔥', 'vape': '💧'
        }.get(prod['type'], '📦')
        
        is_active = " ✅ *АКТИВНИЙ*" if prod_id == active else ""
        text += f"{emoji} *{prod['name']}*{is_active}\n"
        text += f"   💵 {prod['price_per_unit']:.2f} ₴/шт\n\n"
    
    bot.reply_to(
        message,
        text,
        parse_mode='Markdown',
        reply_markup=main_menu(user_id)
    )

# ====================================================
# 8. НОВИЙ ПРОДУКТ
# ====================================================

@bot.message_handler(func=lambda message: message.text == "➕ Новий продукт")
def add_product(message):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🚬 Сигарети", callback_data="add_cigarettes"),
        types.InlineKeyboardButton("💨 Кальян", callback_data="add_hookah"),
        types.InlineKeyboardButton("👃 Снюс", callback_data="add_snus"),
        types.InlineKeyboardButton("🔥 Айкос", callback_data="add_iqos"),
        types.InlineKeyboardButton("💧 Електронна", callback_data="add_vape"),
        types.InlineKeyboardButton("❌ Скасувати", callback_data="add_cancel")
    )
    
    bot.reply_to(
        message,
        "📦 *Оберіть тип продукту:*\n\n"
        "Після вибору введи:\n"
        "`Назва; Ціна; Кількість`\n\n"
        "📌 Наприклад:\n"
        "`Вінстон X Style 6; 170; 20`\n"
        "`Кальян; 150; 1`",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_'))
def handle_add(call):
    user_id = str(call.from_user.id)
    product_type = call.data.replace('add_', '')
    
    if product_type == 'cancel':
        bot.edit_message_text(
            "❌ Скасовано.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id)
        return
    
    msg = bot.send_message(
        call.message.chat.id,
        f"✏️ Введи дані для *{product_type}*:\n\n"
        "Формат: `Назва; Ціна; Кількість`",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, save_product, product_type)
    bot.answer_callback_query(call.id)

def save_product(message, product_type):
    user_id = str(message.from_user.id)
    try:
        parts = message.text.split(';')
        if len(parts) != 3:
            raise ValueError
        
        name = parts[0].strip()
        price = float(parts[1].strip().replace(',', '.'))
        count = int(parts[2].strip())
        
        if price <= 0 or count <= 0:
            raise ValueError
        
        data = load_data()
        product_id = f"{product_type}_{len(data[user_id]['products'])}"
        
        data[user_id]['products'][product_id] = {
            'id': product_id,
            'name': name,
            'type': product_type,
            'pack_price': price,
            'pack_count': count,
            'price_per_unit': round(price / count, 2)
        }
        
        if data[user_id]['active_product'] is None:
            data[user_id]['active_product'] = product_id
        
        save_data(data)
        
        emoji = {
            'cigarettes': '🚬', 'hookah': '💨', 'snus': '👃',
            'iqos': '🔥', 'vape': '💧'
        }.get(product_type, '📦')
        
        bot.reply_to(
            message,
            f"✅ *Продукт додано!*\n\n"
            f"{emoji} {name}\n"
            f"💰 {price} ₴ за {count} шт\n"
            f"💵 {round(price/count, 2)} ₴/шт\n\n"
            f"_Тепер обери його через «🔄 Змінити продукт»_",
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
        
    except:
        bot.reply_to(
            message,
            "❌ Помилка! Використовуй формат:\n"
            "`Назва; Ціна; Кількість`\n\n"
            "Наприклад: `Вінстон; 170; 20`",
            parse_mode='Markdown'
        )

# ====================================================
# 9. ЗМІНИТИ ПРОДУКТ
# ====================================================

@bot.message_handler(func=lambda message: message.text == "🔄 Змінити продукт")
def change_product(message):
    user_id = str(message.from_user.id)
    data = load_data()
    products = data[user_id]['products']
    
    if not products:
        bot.reply_to(
            message,
            "❌ Спочатку додай продукт через «➕ Новий продукт»",
            reply_markup=main_menu(user_id)
        )
        return
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for prod_id, prod in products.items():
        emoji = {
            'cigarettes': '🚬', 'hookah': '💨', 'snus': '👃',
            'iqos': '🔥', 'vape': '💧'
        }.get(prod['type'], '📦')
        
        is_active = " ✅" if prod_id == data[user_id]['active_product'] else ""
        keyboard.add(
            types.InlineKeyboardButton(
                f"{emoji} {prod['name']} ({prod['price_per_unit']:.2f} ₴){is_active}",
                callback_data=f"choose_{prod_id}"
            )
        )
    
    keyboard.add(types.InlineKeyboardButton("❌ Закрити", callback_data="choose_close"))
    
    bot.reply_to(
        message,
        "🔄 *Оберіть активний продукт:*\n\n"
        "✅ = поточний активний",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('choose_'))
def handle_choose(call):
    user_id = str(call.from_user.id)
    
    if call.data == "choose_close":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)
        return
    
    prod_id = call.data.replace('choose_', '')
    data = load_data()
    
    if prod_id in data[user_id]['products']:
        data[user_id]['active_product'] = prod_id
        save_data(data)
        
        prod = data[user_id]['products'][prod_id]
        bot.edit_message_text(
            f"✅ *Активний продукт:* {prod['name']}",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.send_message(
            call.message.chat.id,
            "✅ Готово! Тепер натискай «🚬 Покурив!»",
            reply_markup=main_menu(user_id)
        )
    else:
        bot.answer_callback_query(call.id, "❌ Продукт не знайдено")
    
    bot.answer_callback_query(call.id)

# ====================================================
# 10. АДМІН-ПАНЕЛЬ (ТІЛЬКИ ДЛЯ АДМІНА)
# ====================================================

@bot.message_handler(func=lambda message: message.text == "⚙️ Адмін-панель")
def admin_panel(message):
    user_id = str(message.from_user.id)
    
    if not is_admin(user_id):
        bot.reply_to(
            message,
            "⛔ Доступ заборонено.",
            reply_markup=main_menu(user_id)
        )
        return
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("📊 Експорт Excel", callback_data="admin_export"),
        types.InlineKeyboardButton("👥 Всі користувачі", callback_data="admin_users"),
        types.InlineKeyboardButton("📈 Загальна статистика", callback_data="admin_stats"),
        types.InlineKeyboardButton("📤 Отримати JSON", callback_data="admin_getdata"),
        types.InlineKeyboardButton("🗑️ Очистити базу", callback_data="admin_clear"),
        types.InlineKeyboardButton("❌ Закрити", callback_data="admin_close")
    )
    
    bot.reply_to(
        message,
        "👑 *Адмін-панель*\n\n"
        "Оберіть дію:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin(call):
    user_id = str(call.from_user.id)
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔ Доступ заборонено!")
        return
    
    data = load_data()
    
    if call.data == "admin_export":
        if not data:
            bot.edit_message_text("📭 Немає даних.", call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id)
            return
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(['User ID', "Ім'я", 'Продукт', 'Тип', 'Дата', 'Час', 'Ціна (грн)'])
        
        for uid, user_data in data.items():
            for record in user_data.get('history', []):
                writer.writerow([
                    uid,
                    user_data['user_info'].get('first_name', ''),
                    record['product_name'],
                    record['product_type'],
                    record['date'],
                    record['time'],
                    f"{record['price']:.2f}"
                ])
        
        csv_content = output.getvalue().encode('utf-8-sig')
        bot.send_document(
            call.message.chat.id,
            ('csv', csv_content),
            caption=f"📊 Експорт даних\n📅 {get_kyiv_date().isoformat()}"
        )
        bot.edit_message_text("✅ Файл надіслано.", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_users":
        text = "👥 *Всі користувачі:*\n\n"
        for uid, user_data in data.items():
            info = user_data['user_info']
            history_count = len(user_data.get('history', []))
            text += f"• {info.get('first_name', 'Без імені')} (@{info.get('username', '')})\n"
            text += f"  ID: `{uid}` | Записів: {history_count}\n\n"
        
        if not data:
            text = "📭 Немає користувачів."
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_stats":
        total_users = len(data)
        total_smokes = 0
        total_spent = 0.0
        product_stats = {}
        
        for uid, user_data in data.items():
            for record in user_data.get('history', []):
                total_smokes += 1
                total_spent += record['price']
                name = record['product_name']
                if name not in product_stats:
                    product_stats[name] = {'count': 0, 'spent': 0}
                product_stats[name]['count'] += 1
                product_stats[name]['spent'] += record['price']
        
        text = f"📈 *Загальна статистика*\n\n"
        text += f"👥 Користувачів: *{total_users}*\n"
        text += f"🚬 Всього сесій: *{total_smokes}*\n"
        text += f"💰 Всього витрачено: *{total_spent:.2f}* ₴\n\n"
        text += "*По продуктах:*\n"
        for name, stats in product_stats.items():
            text += f"   • {name}: {stats['count']} шт ({stats['spent']:.2f} ₴)\n"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_getdata":
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'rb') as f:
                bot.send_document(
                    call.message.chat.id,
                    f,
                    caption=f"📁 База даних JSON\n📅 {get_kyiv_date().isoformat()}"
                )
            bot.edit_message_text("✅ Файл надіслано.", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text("❌ Файл не знайдено.", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_clear":
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("⚠️ Так, очистити ВСЕ", callback_data="admin_clear_confirm"),
            types.InlineKeyboardButton("❌ Ні, скасувати", callback_data="admin_clear_cancel")
        )
        bot.edit_message_text(
            "⚠️ *УВАГА!* Ти впевнений?\n\n"
            "Всі дані будуть видалені безповоротно!",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_clear_confirm":
        save_data({})
        bot.edit_message_text(
            "🗑️ *ВСІ ДАНІ ОЧИЩЕНО!*",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_clear_cancel":
        bot.edit_message_text(
            "❌ Очищення скасовано.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_close":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)

# ====================================================
# 11. ОБРОБКА НЕВІДОМИХ ПОВІДОМЛЕНЬ
# ====================================================

@bot.message_handler(func=lambda message: True)
def unknown_message(message):
    """Відповідає на невідомі повідомлення"""
    bot.reply_to(
        message,
        "❓ Скористайся кнопками в меню 👇",
        reply_markup=main_menu(message.from_user.id)
    )

# ====================================================
# 12. ЗАПУСК
# ====================================================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 SmokeTracker Bot")
    print("=" * 50)
    print(f"👑 Адмін ID: {ADMIN_ID}")
    print(f"🕐 Київський час: {get_kyiv_time().strftime('%H:%M:%S')}")
    print(f"📁 Файл даних: {DATA_FILE}")
    print("=" * 50)
    print("✅ Бот готовий до роботи!")
    bot.polling(none_stop=True)
