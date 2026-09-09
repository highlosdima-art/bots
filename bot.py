import os
import json
from datetime import datetime, date, timedelta
import telebot
from telebot import types
import io
import csv

# ====================================================
# 1. ТОКЕН ТА АДМІН
# ====================================================
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN не знайдено!")

bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 1081116211  # ТВІЙ ID

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
                'registered_at': datetime.now().isoformat()
            },
            'products': {},
            'active_product': None,
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
# 3. ДОДАВАННЯ ПРОДУКТУ
# ====================================================

@bot.message_handler(commands=['addproduct'])
def add_product_start(message):
    user_id = str(message.from_user.id)
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🚬 Сигарети", callback_data="prod_cigarettes"),
        types.InlineKeyboardButton("💨 Кальян", callback_data="prod_hookah"),
        types.InlineKeyboardButton("👃 Снюс", callback_data="prod_snus"),
        types.InlineKeyboardButton("🔥 Айкос", callback_data="prod_iqos"),
        types.InlineKeyboardButton("💧 Електронна", callback_data="prod_vape"),
        types.InlineKeyboardButton("❌ Скасувати", callback_data="prod_cancel")
    )
    
    bot.reply_to(
        message,
        "📦 *Оберіть тип продукту:*\n\n"
        "Після вибору введіть назву, ціну та кількість у форматі:\n"
        "`Назва; Ціна; Кількість`\n\n"
        "Наприклад: `Вінстон X Style 6; 170; 20`",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('prod_'))
def handle_product_type(call):
    user_id = str(call.from_user.id)
    product_type = call.data.replace('prod_', '')
    
    if product_type == 'cancel':
        bot.edit_message_text(
            "❌ Додавання продукту скасовано.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.answer_callback_query(call.id)
        return
    
    # Зберігаємо тип продукту в тимчасовий стан
    # Використаємо callback.data для передачі
    msg = bot.send_message(
        call.message.chat.id,
        f"✏️ Введи дані для *{product_type}*:\n\n"
        "Формат: `Назва; Ціна за пачку; Кількість в пачці`\n"
        "Наприклад: `Вінстон X Style 6; 170; 20`\n\n"
        "Для кальяну: `Кальян; 150; 1` (де 1 = одна чаша)",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, save_product, product_type)
    bot.answer_callback_query(call.id)

def save_product(message, product_type):
    user_id = str(message.from_user.id)
    try:
        parts = message.text.split(';')
        if len(parts) != 3:
            raise ValueError("Потрібно 3 частини: Назва; Ціна; Кількість")
        
        name = parts[0].strip()
        price = float(parts[1].strip().replace(',', '.'))
        count = int(parts[2].strip())
        
        if price <= 0 or count <= 0:
            raise ValueError("Ціна та кількість мають бути > 0")
        
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
        
        # Якщо це перший продукт — робимо його активним
        if data[user_id]['active_product'] is None:
            data[user_id]['active_product'] = product_id
        
        save_data(data)
        
        # Показуємо тип продукту емодзі
        emoji = {
            'cigarettes': '🚬',
            'hookah': '💨',
            'snus': '👃',
            'iqos': '🔥',
            'vape': '💧'
        }.get(product_type, '📦')
        
        bot.reply_to(
            message,
            f"✅ *Продукт додано!*\n\n"
            f"{emoji} {name}\n"
            f"💰 Ціна: {price} ₴ за {count} шт\n"
            f"💵 За 1 шт: {round(price/count, 2)} ₴\n\n"
            f"Тепер використовуй `/choose` щоб вибрати активний продукт",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot.reply_to(
            message,
            f"❌ Помилка: {e}\n\n"
            "Спробуй ще раз у форматі:\n"
            "`Назва; Ціна; Кількість`\n"
            "Наприклад: `Вінстон; 170; 20`",
            parse_mode='Markdown'
        )

# ====================================================
# 4. ВИБІР АКТИВНОГО ПРОДУКТУ
# ====================================================

@bot.message_handler(commands=['choose'])
def choose_product(message):
    user_id = str(message.from_user.id)
    data = load_data()
    products = data[user_id]['products']
    
    if not products:
        bot.reply_to(
            message,
            "❌ У тебе ще немає продуктів.\n"
            "Додай продукт: `/addproduct`",
            parse_mode='Markdown'
        )
        return
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for prod_id, prod in products.items():
        emoji = {
            'cigarettes': '🚬',
            'hookah': '💨',
            'snus': '👃',
            'iqos': '🔥',
            'vape': '💧'
        }.get(prod['type'], '📦')
        
        is_active = "✅ " if prod_id == data[user_id]['active_product'] else ""
        keyboard.add(
            types.InlineKeyboardButton(
                f"{is_active}{emoji} {prod['name']} ({prod['price_per_unit']} ₴/шт)",
                callback_data=f"choose_{prod_id}"
            )
        )
    
    bot.reply_to(
        message,
        "🔀 *Оберіть активний продукт:*\n\n"
        "Він буде використовуватися за замовчуванням для `/smoke`",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('choose_'))
def handle_choose_product(call):
    user_id = str(call.from_user.id)
    prod_id = call.data.replace('choose_', '')
    
    data = load_data()
    if prod_id in data[user_id]['products']:
        data[user_id]['active_product'] = prod_id
        save_data(data)
        
        prod = data[user_id]['products'][prod_id]
        bot.edit_message_text(
            f"✅ *Активний продукт змінено!*\n\n"
            f"🚬 {prod['name']}\n"
            f"💵 Ціна: {prod['price_per_unit']} ₴ за 1 шт",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
    else:
        bot.edit_message_text(
            "❌ Продукт не знайдено.",
            call.message.chat.id,
            call.message.message_id
        )
    
    bot.answer_callback_query(call.id)

# ====================================================
# 5. ОНОВЛЕНИЙ /SMOKE З ВИБОРОМ ЧАСУ
# ====================================================

# Тимчасове сховище для часу
user_temp_time = {}

@bot.message_handler(commands=['smoke'])
def smoke_start(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    # Перевіряємо, чи є активний продукт
    if data[user_id]['active_product'] is None:
        bot.reply_to(
            message,
            "❌ Спочатку додай продукт: `/addproduct`\n"
            "Потім обери його: `/choose`",
            parse_mode='Markdown'
        )
        return
    
    # Пропонуємо вибрати час
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    now = datetime.now()
    keyboard.add(
        types.InlineKeyboardButton("🕐 Зараз", callback_data="time_now"),
        types.InlineKeyboardButton("⬅️ -1 год", callback_data="time_minus_1"),
        types.InlineKeyboardButton("➡️ +1 год", callback_data="time_plus_1"),
        types.InlineKeyboardButton("⏪ -30 хв", callback_data="time_minus_30"),
        types.InlineKeyboardButton("⏩ +30 хв", callback_data="time_plus_30"),
        types.InlineKeyboardButton("✏️ Ввести час", callback_data="time_custom")
    )
    
    # Показуємо поточний активний продукт
    prod = data[user_id]['products'][data[user_id]['active_product']]
    
    bot.reply_to(
        message,
        f"🚬 *Викурив {prod['name']}*\n"
        f"💵 Ціна: {prod['price_per_unit']} ₴\n\n"
        f"🕐 *Коли це було?*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
def handle_time_selection(call):
    user_id = str(call.from_user.id)
    data = load_data()
    
    now = datetime.now()
    selected_time = now
    
    if call.data == "time_now":
        selected_time = now
    elif call.data == "time_minus_1":
        selected_time = now - timedelta(hours=1)
    elif call.data == "time_plus_1":
        selected_time = now + timedelta(hours=1)
    elif call.data == "time_minus_30":
        selected_time = now - timedelta(minutes=30)
    elif call.data == "time_plus_30":
        selected_time = now + timedelta(minutes=30)
    elif call.data == "time_custom":
        msg = bot.send_message(
            call.message.chat.id,
            "✏️ Введи час у форматі `ГГ:ХХ` (наприклад: `15:19`):",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, process_custom_time)
        bot.answer_callback_query(call.id)
        return
    
    # Зберігаємо час і продовжуємо
    user_temp_time[user_id] = selected_time
    process_smoke(call.message, user_id, selected_time)
    bot.answer_callback_query(call.id)

def process_custom_time(message):
    user_id = str(message.from_user.id)
    try:
        time_str = message.text.strip()
        hour, minute = map(int, time_str.split(':'))
        
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Неправильний час")
        
        now = datetime.now()
        selected_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Якщо час більший за поточний — значить це вчора
        if selected_time > now:
            selected_time = selected_time - timedelta(days=1)
        
        user_temp_time[user_id] = selected_time
        process_smoke(message, user_id, selected_time)
        
    except:
        bot.reply_to(
            message,
            "❌ Неправильний формат. Використовуй `ГГ:ХХ` (наприклад: `15:19`)",
            parse_mode='Markdown'
        )

def process_smoke(message, user_id, smoke_time):
    check_reset(user_id)
    
    data = load_data()
    prod_id = data[user_id]['active_product']
    prod = data[user_id]['products'][prod_id]
    
    # Запис в історію
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
    
    # Емодзі для типу
    emoji = {
        'cigarettes': '🚬',
        'hookah': '💨',
        'snus': '👃',
        'iqos': '🔥',
        'vape': '💧'
    }.get(prod['type'], '📦')
    
    response = f"""{emoji} *{prod['name']}* викурено!

💸 Списано: *{prod['price_per_unit']:.2f} ₴*
🕐 Час: {smoke_time.strftime('%H:%M')}

📊 *Сьогодні:*
🚬 Всього: *{data[user_id]['daily']['count']}* шт
💰 Витрачено: *{data[user_id]['daily']['spent']:.2f}* ₴"""
    
    bot.reply_to(message, response, parse_mode='Markdown')

# ====================================================
# 6. ОНОВЛЕНИЙ /STATS
# ====================================================

@bot.message_handler(commands=['stats'])
def stats(message):
    user_id = str(message.from_user.id)
    check_reset(user_id)
    
    data = load_data()
    user = data[user_id]
    
    # Статистика по продуктах
    product_stats = {}
    for record in user['history']:
        prod_name = record['product_name']
        if prod_name not in product_stats:
            product_stats[prod_name] = {'count': 0, 'spent': 0}
        product_stats[prod_name]['count'] += 1
        product_stats[prod_name]['spent'] += record['price']
    
    # Текст статистики
    text = f"""📊 *Твоя статистика*

👤 {user['user_info']['first_name']}

📆 *Сьогодні:*
🚬 Викурено: *{user['daily']['count']}* шт
💰 Витрачено: *{user['daily']['spent']:.2f}* ₴

📈 *За весь час:*
🚬 Всього: *{user['total']['count'] + user['daily']['count']}* шт
💰 Всього: *{user['total']['spent'] + user['daily']['spent']:.2f}* ₴

📋 *По продуктах:*\n"""
    
    for name, stats in product_stats.items():
        text += f"   • {name}: {stats['count']} шт ({stats['spent']:.2f} ₴)\n"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# ====================================================
# 7. ЕКСПОРТ В EXCEL (З ГРАФІКАМИ)
# ====================================================

@bot.message_handler(commands=['export'])
def export_excel(message):
    user_id = str(message.from_user.id)
    
    if not is_admin(user_id):
        bot.reply_to(message, "⛔ Доступ заборонено.")
        return
    
    data = load_data()
    if not data:
        bot.reply_to(message, "📭 Немає даних!")
        return
    
    # Створюємо CSV
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # Заголовки
    writer.writerow([
        'User ID', 
        "Ім'я",
        'Продукт',
        'Тип',
        'Дата',
        'Час',
        'Ціна (грн)'
    ])
    
    # Всі записи
    for user_id, user_data in data.items():
        for record in user_data.get('history', []):
            writer.writerow([
                user_id,
                user_data['user_info'].get('first_name', ''),
                record['product_name'],
                record['product_type'],
                record['date'],
                record['time'],
                f"{record['price']:.2f}"
            ])
    
    csv_content = output.getvalue().encode('utf-8-sig')
    filename = f"smoke_export_{date.today().isoformat()}.csv"
    
    bot.send_document(
        message.chat.id,
        ('csv', csv_content),
        caption=f"📊 Повна статистика\n📅 {date.today().isoformat()}\n"
                f"👥 Користувачів: {len(data)}"
    )

# ====================================================
# 8. ІНШІ КОМАНДИ
# ====================================================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    get_user_data(user_id)
    
    text = f"""🚬 *Вітаю в розширеному лічильнику!*

📌 *Команди:*
/addproduct - додати продукт
/choose - обрати активний продукт
/smoke - викурити (з вибором часу)
/stats - статистика
/export - вивантажити в Excel (тільки адмін)

📦 *Типи продуктів:*
🚬 Сигарети
💨 Кальян
👃 Снюс
🔥 Айкос
💧 Електронна

💡 *Порада:* Додай свої продукти через /addproduct!"""
    
    bot.reply_to(message, text, parse_mode='Markdown')

# ====================================================
# 9. ЗАПУСК
# ====================================================

if __name__ == '__main__':
    print("🤖 Бот запущено!")
    print(f"👑 Адмін ID: {ADMIN_ID}")
    bot.polling(none_stop=True)
