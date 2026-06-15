"""
Telegram Bot для управления заказами
Обрабатывает callback кнопки и управляет статусом заказов
"""

import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler
from telegram.error import TelegramError

# =========================================
# КОНФИГУРАЦИЯ
# =========================================
TELEGRAM_BOT_TOKEN = '8747837582:AAHq7B54qPq_tG_9ZlkOzZ2zcZsTiH1kj0k'
TELEGRAM_CHAT_ID = -1001003794190290

# Состояния для ConversationHandler
WAITING_FOR_CANCEL_REASON = 1

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище данных о заказах (в продакшене используй БД)
orders_data = {}
user_contexts = {}

# =========================================
# CALLBACK HANDLERS
# =========================================

async def button_accept_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки 'Принять заказ'"""
    
    query = update.callback_query
    await query.answer()
    
    try:
        # Извлекаем order_id из callback_data
        callback_data = query.data
        order_id = callback_data.replace('accept_order_', '')
        
        # Получаем информацию о пользователе
        user_id = query.from_user.id
        user_name = query.from_user.first_name or 'Исполнитель'
        
        # Отправляем запрос на бэкенд
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post('http://localhost:5000/api/accept-order', json={
                'order_id': order_id,
                'executor_name': user_name,
                'executor_id': user_id
            }) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Редактируем исходное сообщение
                    text = f"""
✅ <b>Заказ #{order_id} ПРИНЯТ</b>

👤 <b>Исполнитель:</b> {user_name}
🎁 <b>Пакет:</b> (смотри выше)
💰 <b>Сумма:</b> (смотри выше)

⏳ <b>Статус:</b> В обработке...

<i>Исполнитель начал обработку заказа. Ожидаем завершения!</i>
"""
                    
                    keyboard = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton('✓ Заказ выполнен', callback_data=f'complete_order_{order_id}'),
                            InlineKeyboardButton('❌ Отмена', callback_data=f'cancel_order_{order_id}')
                        ]
                    ])
                    
                    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode='HTML')
                    
                    # Отправляем личное сообщение исполнителю
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ Ты принял заказ #{order_id}!\n\nЖди чека в группе и выполни заказ.",
                        parse_mode='HTML'
                    )
                    
                    logger.info(f"Order {order_id} accepted by {user_name} ({user_id})")
                else:
                    await query.edit_message_text(text="❌ Ошибка при принятии заказа")
                    
    except Exception as e:
        logger.error(f"Error in button_accept_order: {e}")
        await query.edit_message_text(text=f"❌ Произошла ошибка: {str(e)}")

async def button_complete_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки 'Заказ выполнен'"""
    
    query = update.callback_query
    await query.answer()
    
    try:
        callback_data = query.data
        order_id = callback_data.replace('complete_order_', '')
        
        user_id = query.from_user.id
        user_name = query.from_user.first_name or 'Исполнитель'
        
        # Отправляем запрос на бэкенд
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post('http://localhost:5000/api/complete-order', json={
                'order_id': order_id
            }) as resp:
                if resp.status == 200:
                    text = f"""
🎉 <b>Заказ #{order_id} ВЫПОЛНЕН!</b>

✅ <b>Статус:</b> Завершено
👤 <b>Исполнитель:</b> {user_name}

<i>Спасибо за быстрое выполнение! 🚀</i>
"""
                    
                    await query.edit_message_text(text=text, parse_mode='HTML')
                    
                    # Отправляем личное сообщение исполнителю
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"🎉 Заказ #{order_id} успешно завершён!\n\nСпасибо за работу! 💪",
                        parse_mode='HTML'
                    )
                    
                    logger.info(f"Order {order_id} completed by {user_name}")
                else:
                    await query.edit_message_text(text="❌ Ошибка при завершении заказа")
                    
    except Exception as e:
        logger.error(f"Error in button_complete_order: {e}")
        await query.edit_message_text(text=f"❌ Произошла ошибка: {str(e)}")

async def button_cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки 'Отмена' - запрашивает причину"""
    
    query = update.callback_query
    await query.answer()
    
    try:
        callback_data = query.data
        order_id = callback_data.replace('cancel_order_', '')
        
        user_id = query.from_user.id
        
        # Сохраняем контекст
        user_contexts[user_id] = {'order_id': order_id}
        
        # Отправляем сообщение с вариантами причин отмены
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('❌ Ошибка платежа', callback_data=f'cancel_reason_payment_error_{order_id}')],
            [InlineKeyboardButton('❌ Нет средств', callback_data=f'cancel_reason_no_funds_{order_id}')],
            [InlineKeyboardButton('❌ Игрок не ответил', callback_data=f'cancel_reason_no_response_{order_id}')],
            [InlineKeyboardButton('❌ Другое', callback_data=f'cancel_reason_other_{order_id}')]
        ])
        
        text = f"""
❓ <b>Почему ты отменяешь заказ #{order_id}?</b>

Выбери причину отмены:
"""
        
        await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in button_cancel_order: {e}")
        await query.edit_message_text(text=f"❌ Произошла ошибка: {str(e)}")

async def button_cancel_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора причины отмены"""
    
    query = update.callback_query
    await query.answer()
    
    try:
        callback_data = query.data
        parts = callback_data.split('_')
        reason_key = '_'.join(parts[2:-1])
        order_id = parts[-1]
        
        user_id = query.from_user.id
        user_name = query.from_user.first_name or 'Исполнитель'
        
        # Преобразуем ключ причины в текст
        reasons = {
            'payment_error': 'Ошибка платежа',
            'no_funds': 'Нет средств на счёте',
            'no_response': 'Игрок не ответил',
            'other': 'Другая причина'
        }
        
        reason_text = reasons.get(reason_key, 'Не указана')
        
        # Отправляем запрос на бэкенд
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post('http://localhost:5000/api/cancel-order', json={
                'order_id': order_id,
                'reason': reason_text,
                'executor_name': user_name
            }) as resp:
                if resp.status == 200:
                    text = f"""
❌ <b>Заказ #{order_id} ОТМЕНЁН</b>

📝 <b>Причина:</b> {reason_text}
👤 <b>Отменил:</b> {user_name}

<i>Заказ возвращен в очередь. Может ли кто-то другой его взять?</i>
"""
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton('✅ Принять заказ', callback_data=f'accept_order_{order_id}')]
                    ])
                    
                    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode='HTML')
                    
                    # Отправляем личное сообщение исполнителю
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"❌ Заказ #{order_id} отменён.\n\nПричина: {reason_text}",
                        parse_mode='HTML'
                    )
                    
                    logger.info(f"Order {order_id} cancelled by {user_name}: {reason_text}")
                else:
                    await query.edit_message_text(text="❌ Ошибка при отмене заказа")
                    
    except Exception as e:
        logger.error(f"Error in button_cancel_reason: {e}")
        await query.edit_message_text(text=f"❌ Произошла ошибка: {str(e)}")

# =========================================
# КОМАНДЫ
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    
    user = update.effective_user
    text = f"""
👋 Привет, {user.first_name}!

Я бот для управления заказами Diamond Shop.

🎁 <b>Как это работает:</b>
1️⃣ Клиент отправляет заказ через сайт
2️⃣ Я отправляю заказ в группу с кнопками
3️⃣ Ты нажимаешь "Принять заказ"
4️⃣ После выполнения нажимаешь "Заказ выполнен"
5️⃣ Если что-то не так, нажимаешь "Отмена" и указываешь причину

📊 <b>Мои команды:</b>
/orders - Список всех заказов
/pending - Заказы в ожидании
/active - Активные заказы
/completed - Завершённые заказы

Готов помочь! 🚀
"""
    
    await update.message.reply_text(text, parse_mode='HTML')

async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает статистику заказов"""
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:5000/api/orders') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    orders = data.get('orders', {})
                    
                    # Подсчитываем статусы
                    pending = sum(1 for o in orders.values() if o['status'] == 'pending')
                    accepted = sum(1 for o in orders.values() if o['status'] == 'accepted')
                    completed = sum(1 for o in orders.values() if o['status'] == 'completed')
                    cancelled = sum(1 for o in orders.values() if o['status'] == 'cancelled')
                    
                    text = f"""
📊 <b>СТАТИСТИКА ЗАКАЗОВ</b>

⏳ Ожидают: {pending}
🔄 В обработке: {accepted}
✅ Завершено: {completed}
❌ Отменено: {cancelled}

📈 <b>Всего:</b> {len(orders)}
"""
                    
                    await update.message.reply_text(text, parse_mode='HTML')
                else:
                    await update.message.reply_text("❌ Ошибка при получении данных")
                    
    except Exception as e:
        logger.error(f"Error in orders_command: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")

# =========================================
# ГЛАВНАЯ ФУНКЦИЯ
# =========================================

async def main() -> None:
    """Запускает бота"""
    
    # Создаём Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Добавляем обработчики callback кнопок
    application.add_handler(CallbackQueryHandler(button_accept_order, pattern='^accept_order_'))
    application.add_handler(CallbackQueryHandler(button_complete_order, pattern='^complete_order_'))
    application.add_handler(CallbackQueryHandler(button_cancel_order, pattern='^cancel_order_'))
    application.add_handler(CallbackQueryHandler(button_cancel_reason, pattern='^cancel_reason_'))
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('orders', orders_command))
    
    # Запускаем бота
    logger.info("Starting Telegram Bot...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    asyncio.run(main())
