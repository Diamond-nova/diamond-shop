"""
Flask Backend для Diamond Shop с интеграцией Telegram Bot
Обрабатывает заказы, загружает чеки и управляет статусом заказов
"""

import os
import json
import uuid
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import aiohttp
import logging

# =========================================
# КОНФИГУРАЦИЯ
# =========================================
TELEGRAM_BOT_TOKEN = '8747837582:AAHq7B54qPq_tG_9ZlkOzZ2zcZsTiH1kj0k'
TELEGRAM_CHAT_ID = -1001003794190290  # Приватная группа
CONTACT_NUMBER = '+992 91 776 01 50'  # Номер контакта для обеих платёжных систем
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# =========================================
# ИНИЦИАЛИЗАЦИЯ
# =========================================
app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Создаём папку для загрузок
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище заказов (в продакшене используй БД)
orders_db = {}

# =========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================
def allowed_file(filename):
    """Проверяет расширение файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

async def send_telegram_message(chat_id, text, parse_mode='HTML'):
    """Отправляет сообщение в Telegram"""
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                return await resp.json()
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None

async def send_telegram_photo(chat_id, photo_path, caption='', parse_mode='HTML'):
    """Отправляет фото в Telegram"""
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto'
    
    try:
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {
                'chat_id': chat_id,
                'caption': caption,
                'parse_mode': parse_mode
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, files=files) as resp:
                    return await resp.json()
    except Exception as e:
        logger.error(f"Error sending photo: {e}")
        return None

async def send_telegram_inline_buttons(chat_id, text, buttons, parse_mode='HTML'):
    """Отправляет сообщение с inline кнопками"""
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    
    keyboard = {
        'inline_keyboard': buttons
    }
    
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'reply_markup': json.dumps(keyboard)
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                return await resp.json()
    except Exception as e:
        logger.error(f"Error sending buttons: {e}")
        return None

# =========================================
# API ENDPOINTS
# =========================================

@app.route('/api/submit-order', methods=['POST'])
def submit_order():
    """Получает заказ от клиента и отправляет в Telegram"""
    
    try:
        # Получаем данные
        player_id = request.form.get('playerId', '').strip()
        package = request.form.get('package', '')
        diamonds = request.form.get('diamonds', '')
        price = request.form.get('price', '')
        payment_method = request.form.get('paymentMethod', '')
        
        # Проверяем файл
        if 'receipt' not in request.files:
            return jsonify({'error': 'Чек не загружен'}), 400
        
        file = request.files['receipt']
        
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Недопустимый формат файла'}), 400
        
        # Сохраняем файл
        order_id = str(uuid.uuid4())[:8].upper()
        filename = secure_filename(f"{order_id}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Сохраняем информацию о заказе
        order_data = {
            'order_id': order_id,
            'player_id': player_id,
            'package': package,
            'diamonds': diamonds,
            'price': price,
            'payment_method': payment_method,
            'receipt_file': filename,
            'status': 'pending',  # pending, accepted, completed, cancelled
            'created_at': datetime.now().isoformat(),
            'accepted_by': None,
            'completed_at': None,
            'cancel_reason': None
        }
        
        orders_db[order_id] = order_data
        
        # Отправляем в Telegram
        asyncio.run(send_order_to_telegram(order_data, filepath))
        
        logger.info(f"Order {order_id} created: {player_id}")
        
        return jsonify({
            'success': True,
            'orderId': order_id,
            'message': 'Заказ успешно отправлен!'
        }), 200
        
    except Exception as e:
        logger.error(f"Error submitting order: {e}")
        return jsonify({'error': str(e)}), 500

async def send_order_to_telegram(order_data, receipt_path):
    """Отправляет заказ в Telegram с кнопками для исполнителей"""
    
    order_id = order_data['order_id']
    player_id = order_data['player_id']
    package = order_data['package']
    diamonds = order_data['diamonds']
    price = order_data['price']
    payment_method = order_data['payment_method']
    
    # Красивый текст заказа
    payment_name = 'DC Next' if payment_method == 'dc-next' else 'Alif Mobi'
    
    text = f"""
🎁 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>

👤 <b>ID игрока:</b> <code>{player_id}</code>
💎 <b>Пакет:</b> {package.upper()} ({diamonds} алмазов)
💰 <b>Сумма:</b> {price} сом.
💳 <b>Способ оплаты:</b> {payment_name}
📱 <b>Номер контакта:</b> <code>{CONTACT_NUMBER}</code>

⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
📊 <b>Статус:</b> ⏳ Ожидает принятия

<i>Нажми кнопку ниже, чтобы принять заказ!</i>
"""
    
    # Кнопки для исполнителей
    buttons = [
        [
            {
                'text': '✅ Принять заказ',
                'callback_data': f'accept_order_{order_id}'
            }
        ]
    ]
    
    # Отправляем сообщение с кнопками
    await send_telegram_inline_buttons(TELEGRAM_CHAT_ID, text, buttons)
    
    # Отправляем фото чека
    caption = f"📸 <b>Чек для заказа #{order_id}</b>\n\nID игрока: <code>{player_id}</code>"
    await send_telegram_photo(TELEGRAM_CHAT_ID, receipt_path, caption)

@app.route('/api/accept-order', methods=['POST'])
def accept_order():
    """Исполнитель принимает заказ"""
    
    try:
        data = request.json
        order_id = data.get('order_id')
        executor_name = data.get('executor_name', 'Исполнитель')
        executor_id = data.get('executor_id')
        
        if order_id not in orders_db:
            return jsonify({'error': 'Заказ не найден'}), 404
        
        order = orders_db[order_id]
        
        if order['status'] != 'pending':
            return jsonify({'error': 'Заказ уже обработан'}), 400
        
        # Обновляем статус
        order['status'] = 'accepted'
        order['accepted_by'] = {
            'name': executor_name,
            'id': executor_id,
            'accepted_at': datetime.now().isoformat()
        }
        
        # Отправляем уведомление в группу
        text = f"""
✅ <b>Заказ #{order_id} ПРИНЯТ</b>

👤 <b>Исполнитель:</b> {executor_name}
🎁 <b>Пакет:</b> {order['package'].upper()} ({order['diamonds']} алмазов)
💰 <b>Сумма:</b> {order['price']} сом.

⏳ <b>Статус:</b> В обработке...

<i>Исполнитель начал обработку заказа. Ожидаем завершения!</i>
"""
        
        buttons = [
            [
                {
                    'text': '✓ Заказ выполнен',
                    'callback_data': f'complete_order_{order_id}'
                },
                {
                    'text': '❌ Отмена',
                    'callback_data': f'cancel_order_{order_id}'
                }
            ]
        ]
        
        asyncio.run(send_telegram_inline_buttons(TELEGRAM_CHAT_ID, text, buttons))
        
        logger.info(f"Order {order_id} accepted by {executor_name}")
        
        return jsonify({
            'success': True,
            'message': 'Заказ принят!'
        }), 200
        
    except Exception as e:
        logger.error(f"Error accepting order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/complete-order', methods=['POST'])
def complete_order():
    """Исполнитель завершает заказ"""
    
    try:
        data = request.json
        order_id = data.get('order_id')
        
        if order_id not in orders_db:
            return jsonify({'error': 'Заказ не найден'}), 404
        
        order = orders_db[order_id]
        
        if order['status'] != 'accepted':
            return jsonify({'error': 'Заказ не в статусе обработки'}), 400
        
        # Обновляем статус
        order['status'] = 'completed'
        order['completed_at'] = datetime.now().isoformat()
        
        # Отправляем уведомление
        executor_name = order['accepted_by']['name'] if order['accepted_by'] else 'Исполнитель'
        
        text = f"""
🎉 <b>Заказ #{order_id} ВЫПОЛНЕН!</b>

👤 <b>ID игрока:</b> <code>{order['player_id']}</code>
💎 <b>Пакет:</b> {order['package'].upper()} ({order['diamonds']} алмазов)
💰 <b>Сумма:</b> {order['price']} сом.
✅ <b>Исполнитель:</b> {executor_name}

⏰ <b>Завершено:</b> {datetime.now().strftime('%H:%M:%S')}

<i>Спасибо за быстрое выполнение! 🚀</i>
"""
        
        asyncio.run(send_telegram_message(TELEGRAM_CHAT_ID, text))
        
        logger.info(f"Order {order_id} completed")
        
        return jsonify({
            'success': True,
            'message': 'Заказ завершён!'
        }), 200
        
    except Exception as e:
        logger.error(f"Error completing order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cancel-order', methods=['POST'])
def cancel_order():
    """Исполнитель отменяет заказ с причиной"""
    
    try:
        data = request.json
        order_id = data.get('order_id')
        reason = data.get('reason', 'Не указана')
        executor_name = data.get('executor_name', 'Исполнитель')
        
        if order_id not in orders_db:
            return jsonify({'error': 'Заказ не найден'}), 404
        
        order = orders_db[order_id]
        
        if order['status'] not in ['pending', 'accepted']:
            return jsonify({'error': 'Заказ уже завершён'}), 400
        
        # Обновляем статус
        order['status'] = 'cancelled'
        order['cancel_reason'] = reason
        
        # Отправляем уведомление
        text = f"""
❌ <b>Заказ #{order_id} ОТМЕНЁН</b>

👤 <b>ID игрока:</b> <code>{order['player_id']}</code>
💎 <b>Пакет:</b> {order['package'].upper()} ({order['diamonds']} алмазов)
💰 <b>Сумма:</b> {order['price']} сом.

📝 <b>Причина отмены:</b>
<code>{reason}</code>

👤 <b>Отменил:</b> {executor_name}

⏰ <b>Отменено:</b> {datetime.now().strftime('%H:%M:%S')}

<i>Заказ возвращен в очередь. Может ли кто-то другой его взять?</i>
"""
        
        buttons = [
            [
                {
                    'text': '✅ Принять заказ',
                    'callback_data': f'accept_order_{order_id}'
                }
            ]
        ]
        
        asyncio.run(send_telegram_inline_buttons(TELEGRAM_CHAT_ID, text, buttons))
        
        logger.info(f"Order {order_id} cancelled: {reason}")
        
        return jsonify({
            'success': True,
            'message': 'Заказ отменён!'
        }), 200
        
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Получает список всех заказов"""
    
    try:
        # Фильтруем по статусу если нужно
        status = request.args.get('status')
        
        filtered_orders = orders_db
        if status:
            filtered_orders = {k: v for k, v in orders_db.items() if v['status'] == status}
        
        return jsonify({
            'success': True,
            'orders': filtered_orders,
            'total': len(filtered_orders)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/order/<order_id>', methods=['GET'])
def get_order(order_id):
    """Получает информацию о конкретном заказе"""
    
    try:
        if order_id not in orders_db:
            return jsonify({'error': 'Заказ не найден'}), 404
        
        return jsonify({
            'success': True,
            'order': orders_db[order_id]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Проверка здоровья сервера"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()}), 200

# =========================================
# ЗАПУСК
# =========================================
if __name__ == '__main__':
    logger.info("Starting Diamond Shop Backend Server...")
    app.run(debug=True, host='0.0.0.0', port=5000)
