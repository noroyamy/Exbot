import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import json
import os

# 🔐 Токен бота
TOKEN = "8132157647:AAEKgebdk_Q86DZdbPFncwYqhj7YHmrKj20"

# 📂 Файл для хранения данных
DATA_FILE = "data.json"

# 📌 Загрузка данных из JSON
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"admins": [], "pairs": {}, "exchange_requests": []}

# 📌 Сохранение данных в JSON
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# 📥 Инициализация данных
data = load_data()

# 🏦 Данные бота
ADMIN_IDS = data["admins"]  # Список администраторов
PAIRS = data["pairs"]  # Валютные пары
exchange_requests = data["exchange_requests"]  # Список заявок на обмен
user_data = {}
orders = {"exchange": [], "cash_out": []}
user_data = {}
# 🤖 Создание бота
bot = telebot.TeleBot(TOKEN)
# 📌 Главное меню
def main_menu(is_admin=False):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("💱 Обмен"), KeyboardButton("💵 Доп.Услуги"))

    if is_admin:
        markup.add(KeyboardButton("🔧 Админ-панель"))  # Только для администраторов
    
    return markup

# 🚀 Команда /start
@bot.message_handler(commands=["start"])
def start_command(message):
    is_admin = message.chat.id in ADMIN_IDS
    bot.send_message(
        message.chat.id, 
        "🏠 Добро пожаловать! Выберите действие:", 
        reply_markup=main_menu(is_admin)
    )


@bot.message_handler(func=lambda message: message.text == "💱 Обмен")
def exchange_currency(message):
    user_data[message.chat.id] = {"state": "exchange"}
    
    if not PAIRS:
        bot.send_message(message.chat.id, "❌ Доступных валютных пар нет.")
        return

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    for pair in PAIRS.keys():
        markup.add(KeyboardButton(pair))
    markup.add(KeyboardButton("🔙 Назад"))

    bot.send_message(message.chat.id, "Выберите валютную пару:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in PAIRS)
def select_currency_pair(message):
    if user_data.get(message.chat.id, {}).get("state") != "exchange":
        return
    
    pair = message.text
    user_data[message.chat.id] = {"state": "enter_amount", "pair": pair}
    rate = PAIRS[pair]
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🔙 Назад"))
    
    bot.send_message(
        message.chat.id,
        f"💱 Курс {pair}: {rate} USDT\nВведите сумму для обмена:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get("state") == "enter_amount")
def enter_amount(message):
    if message.text == "🔙 Назад":
        user_data.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "⏪ Возвращаемся в меню", reply_markup=main_menu())
        return
    
    try:
        amount = float(message.text)
        pair = user_data[message.chat.id]["pair"]
        rate = PAIRS[pair]
        total = round(amount * rate, 2)
        
        user_data[message.chat.id].update({"amount": amount, "total": total, "state": "confirm"})
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("✅ Подтвердить обмен"), KeyboardButton("🔙 Назад"))
        
        bot.send_message(
            message.chat.id,
            f"🔄 Вы получите: {total} USDT\n"
            f"📥 Переведите {amount} {pair.split('/')[0]} на этот адрес:\n\n"
            f"`Ваш_адрес_кошелька`",
            parse_mode="Markdown",
            reply_markup=markup
        )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка! Введите корректное число.")

@bot.message_handler(func=lambda message: message.text == "✅ Подтвердить обмен")
def confirm_exchange(message):
    if user_data.get(message.chat.id, {}).get("state") != "confirm":
        return
    
    bot.send_message(message.chat.id, "✅ Перевод подтверждён! Теперь отправьте ваш кошелёк для получения средств.")
    user_data[message.chat.id]["state"] = "get_wallet"

@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get("state") == "get_wallet")
def get_wallet_address(message):
    wallet_address = message.text.strip()
    
    if message.chat.id not in user_data:
        bot.send_message(message.chat.id, "❌ Ошибка! Начните обмен заново.")
        return
    
    exchange_info = user_data.pop(message.chat.id)
    
    orders["exchange"].append({
        "user_id": message.chat.id,
        "username": message.from_user.username or f"tg://user?id={message.chat.id}",
        "pair": exchange_info['pair'],
        "amount": exchange_info['amount'],
        "total": exchange_info['total'],
        "wallet": wallet_address
    })
    
    bot.send_message(message.chat.id, "✅ Адрес получен! Ожидайте перевод в течение 10 минут.", reply_markup=main_menu())
    
    for admin_id in ADMIN_IDS:
        bot.send_message(
            admin_id,
            f"📢 Новый обмен!\n"
            f"👤 Пользователь: [{message.from_user.username or message.chat.id}](tg://user?id={message.chat.id})\n"
            f"💱 Пара: {exchange_info['pair']}\n"
            f"💰 Сумма: {exchange_info['amount']} {exchange_info['pair'].split('/')[0]}\n"
            f"💵 К получению: {exchange_info['total']} USDT\n"
            f"📥 Кошелёк пользователя: `{wallet_address}`",
            parse_mode="Markdown"
        )

@bot.message_handler(func=lambda message: message.text == "💵 Доп.Услуги")
def cash_out(message):
    user_data[message.chat.id] = {"state": "cash_out"}
    bot.send_message(message.chat.id, "Введите сумму для обналичивания:")

@bot.message_handler(func=lambda message: user_data.get(message.chat.id, {}).get("state") == "cash_out")
def save_cash_out(message):
    try:
        amount = float(message.text)
        
        orders["cash_out"].append({
            "user_id": message.chat.id,
            "username": message.from_user.username or f"tg://user?id={message.chat.id}",
            "amount": amount
        })
        
        bot.send_message(
            message.chat.id,
            "📩 Запрос на обналичивание отправлен администратору.\nОжидайте ответа.",
            reply_markup=main_menu()
        )
        
        for admin_id in ADMIN_IDS:
            bot.send_message(
                admin_id,
                f"📢 Новый запрос на обналичивание!\n"
                f"👤 Пользователь: [{message.from_user.username or message.chat.id}](tg://user?id={message.chat.id})\n"
                f"💰 Сумма: {amount} USDT",
                parse_mode="Markdown"
            )
        
        user_data.pop(message.chat.id, None)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка! Введите корректное число.")
        
# 📌 Обработчик кнопки "🔧 Админ-панель"
# 📌 Обработчик кнопки "🔧 Админ-панель"
@bot.message_handler(func=lambda message: message.text == "🔧 Админ-панель")
def admin_panel(message):
    if message.chat.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ У вас нет доступа.")
        return

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        "➕ Добавить администратора", "➖ Удалить администратора",
        "➕ Добавить пару", "➖ Удалить пару", "📜 Список пар",
        "📋 Просмотр заявок", "🔙 Назад"
    ]
    
    for btn in buttons:
        markup.add(KeyboardButton(btn))

    bot.send_message(message.chat.id, "🔧 Админ-панель:", reply_markup=markup)

# 📌 Кнопка "🔙 Назад" для возврата в главное меню
@bot.message_handler(func=lambda message: message.text == "🔙 Назад")
def go_back(message):
    is_admin = message.chat.id in ADMIN_IDS
    bot.send_message(message.chat.id, "🔙 Возвращаемся в главное меню...", reply_markup=main_menu(is_admin))
# 📌 Добавление администратора
@bot.message_handler(func=lambda message: message.text == "➕ Добавить администратора")
def add_admin(message):
    user_data[message.chat.id] = {"state": "add_admin"}  # Сбрасываем предыдущее состояние
    msg = bot.send_message(message.chat.id, "Введите ID нового администратора:")
    bot.register_next_step_handler(msg, process_add_admin)

def process_add_admin(message):
    if message.chat.id not in user_data or user_data[message.chat.id].get("state") != "add_admin":
        return  # Игнорируем, если пользователь не в нужном состоянии
    try:
        new_admin_id = int(message.text)
        if new_admin_id in ADMIN_IDS:
            bot.send_message(message.chat.id, "👤 Этот пользователь уже администратор.")
        else:
            ADMIN_IDS.append(new_admin_id)
            save_data(data)
            bot.send_message(message.chat.id, f"✅ Администратор {new_admin_id} добавлен.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректный числовой ID.")

# 📌 Удаление администратора
@bot.message_handler(func=lambda message: message.text == "➖ Удалить администратора")
def remove_admin(message):
    user_data[message.chat.id] = {"state": "remove_admin"}  # Сбрасываем предыдущее состояние
    msg = bot.send_message(message.chat.id, "Введите ID администратора для удаления:")
    bot.register_next_step_handler(msg, process_remove_admin)

def process_remove_admin(message):
    if message.chat.id not in user_data or user_data[message.chat.id].get("state") != "remove_admin":
        return  # Игнорируем, если пользователь не в нужном состоянии
    try:
        admin_id = int(message.text)
        if admin_id in ADMIN_IDS:
            ADMIN_IDS.remove(admin_id)
            save_data(data)
            bot.send_message(message.chat.id, f"✅ Администратор {admin_id} удалён.")
        else:
            bot.send_message(message.chat.id, "❌ Такого администратора нет.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректный ID.")
# 📌 Добавление валютной пары
@bot.message_handler(func=lambda message: message.text == "➕ Добавить пару")
def add_pair(message):
    user_data[message.chat.id] = {"state": "add_pair"}  # Сбрасываем предыдущее состояние
    msg = bot.send_message(message.chat.id, "Введите валютную пару (например, BTC/USDT):")
    bot.register_next_step_handler(msg, process_add_pair)
    
def process_add_pair(message):
    if message.chat.id not in user_data or user_data[message.chat.id].get("state") != "add_pair":
        return  # Игнорируем, если пользователь не в нужном состоянии
    pair = message.text.strip().upper()
    if pair in PAIRS:
        bot.send_message(message.chat.id, "❌ Эта валютная пара уже добавлена.")
        return

    msg = bot.send_message(message.chat.id, f"Введите курс обмена для {pair}:")
    bot.register_next_step_handler(msg, process_add_pair_rate, pair)

def process_add_pair_rate(message, pair):
    if message.chat.id not in user_data or user_data[message.chat.id].get("state") != "add_pair":
        return  # Игнорируем, если пользователь не в нужном состоянии
    try:
        rate = float(message.text)
        PAIRS[pair] = rate
        save_data(data)
        bot.send_message(message.chat.id, f"✅ Валютная пара {pair} добавлена с курсом {rate}.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректное число.")

# 📌 Удаление валютной пары
@bot.message_handler(func=lambda message: message.text == "➖ Удалить пару")
def remove_pair(message):
    user_data[message.chat.id] = {"state": "remove_pair"}  # Сбрасываем предыдущее состояние

    if not PAIRS:
        bot.send_message(message.chat.id, "❌ Нет доступных пар для удаления.")
        return

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    for pair in PAIRS.keys():
        markup.add(KeyboardButton(pair))
    markup.add(KeyboardButton("🔙 Назад"))

    msg = bot.send_message(message.chat.id, "Выберите валютную пару для удаления:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_remove_pair)

def process_remove_pair(message):
    if message.chat.id not in user_data or user_data[message.chat.id].get("state") != "remove_pair":
        return  # Игнорируем, если пользователь не в нужном состоянии
    pair = message.text.strip().upper()
    if pair in PAIRS:
        del PAIRS[pair]
        save_data(data)
        bot.send_message(message.chat.id, f"✅ Валютная пара {pair} удалена.")
    else:
        bot.send_message(message.chat.id, "❌ Такой пары нет.")
# 📌 Просмотр списка валютных пар
@bot.message_handler(func=lambda message: message.text == "📜 Список пар")
def list_pairs(message):
    if not PAIRS:
        bot.send_message(message.chat.id, "❌ Доступных валютных пар нет.")
        return

    pairs_text = "\n".join([f"💱 {pair}: {rate} USDT" for pair, rate in PAIRS.items()])
    bot.send_message(message.chat.id, f"📜 Список валютных пар:\n{pairs_text}")

# 📌 Просмотр заявок
@bot.message_handler(func=lambda message: message.text == "📋 Просмотр заявок")
def view_requests(message):
    if message.chat.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ У вас нет доступа.")
        return

    # Используем заявки из orders, если они там хранятся
    exchange_requests = orders.get("exchange", [])
    cashout_requests = orders.get("cash_out", [])

    if not exchange_requests and not cashout_requests:
        bot.send_message(message.chat.id, "📭 Нет активных заявок.")
        return

    if exchange_requests:
        bot.send_message(message.chat.id, "💱 **Заявки на обмен:**", parse_mode="Markdown")
        for request in exchange_requests:
            text = (
                f"📌 ID: {request.get('id', 'N/A')}\n"
                f"👤 Пользователь: @{request.get('username') or request.get('user_id')}\n"
                f"💱 Пара: {request.get('pair')}\n"
                f"💰 Сумма: {request.get('amount')} {request.get('pair', '').split('/')[0]}\n"
                f"📥 Адрес пользователя: `{request.get('wallet')}`"
            )
            bot.send_message(message.chat.id, text, parse_mode="Markdown")

    if cashout_requests:
        bot.send_message(message.chat.id, "💵 **Заявки на обнал:**", parse_mode="Markdown")
        for request in cashout_requests:
            text = (
                f"📌 ID: {request.get('id', 'N/A')}\n"
                f"👤 Пользователь: @{request.get('username') or request.get('user_id')}\n"
                f"💵 Сумма: {request.get('amount')} USDT"
            )
            bot.send_message(message.chat.id, text, parse_mode="Markdown")
# 📌 Удаление заявки
@bot.message_handler(func=lambda message: message.text.startswith("🗑 Удалить заявку"))
def delete_request(message):
    try:
        # Извлекаем ID заявки из текста сообщения
        request_id = int(message.text.split()[-1])
        
        # Обработка заявок на обмен
        exchange_requests = orders.get("exchange", [])
        exchange_requests = [req for req in exchange_requests if req["id"] != request_id]
        orders["exchange"] = exchange_requests  # Обновляем список заявок на обмен

        # Обработка заявок на обналичивание
        cashout_requests = orders.get("cash_out", [])
        cashout_requests = [req for req in cashout_requests if req["id"] != request_id]
        orders["cash_out"] = cashout_requests  # Обновляем список заявок на обналичивание

        save_data(data)  # Сохраняем изменения
        bot.send_message(message.chat.id, f"✅ Заявка {request_id} удалена.")
    
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка при удалении заявки. Убедитесь, что вы правильно указали ID.")
# 📌 Кнопка "🔙 Назад"
@bot.message_handler(func=lambda message: message.text == "🔙 Назад")
def go_back(message):
    is_admin = message.chat.id in ADMIN_IDS
    bot.send_message(message.chat.id, "🔙 Возвращаемся в главное меню...", reply_markup=main_menu(is_admin))
    
# 🚀 Запуск бота
bot.polling(none_stop=True)