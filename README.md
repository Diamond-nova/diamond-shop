# Diamond Shop - Система управления заказами

Полнофункциональная система для управления заказами алмазов с интеграцией Telegram, поддержкой нескольких способов оплаты и системой управления исполнителями.

## 🎯 Возможности

✅ **Красивый интерфейс сайта** - современный дизайн с неоном и glassmorphism  
✅ **Выбор пакетов** - 6 различных пакетов алмазов с разными ценами  
✅ **Несколько способов оплаты** - DC Next и Alif Mobi  
✅ **Загрузка чеков** - пользователи загружают скриншоты платежей  
✅ **Telegram интеграция** - заказы поступают в приватную группу  
✅ **Система управления заказами** - исполнители принимают, выполняют, отменяют заказы  
✅ **Интерактивные кнопки** - управление заказами через Telegram  
✅ **Отслеживание статуса** - полная история каждого заказа  
✅ **Система отмены** - исполнители могут отменить заказ с указанием причины  

## 📁 Структура проекта

```
diamond-shop/
├── diamond-shop-updated.html    # Фронтенд сайта
├── app.py                       # Flask бэкенд сервер
├── telegram_bot.py              # Telegram бот для управления заказами
├── requirements.txt             # Зависимости Python
├── uploads/                     # Папка для загруженных чеков
└── README.md                    # Этот файл
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Запуск бэкенда

```bash
python app.py
```

Сервер запустится на `http://localhost:5000`

### 3. Запуск Telegram бота (в отдельном терминале)

```bash
python telegram_bot.py
```

### 4. Открыть сайт

Открой файл `diamond-shop-updated.html` в браузере или разместить на веб-сервере.

## ⚙️ Конфигурация

### Telegram Bot Token и Chat ID

В файлах `app.py` и `telegram_bot.py` найди строки:

```python
TELEGRAM_BOT_TOKEN = '8747837582:AAHq7B54qPq_tG_9ZlkOzZ2zcZsTiH1kj0k'
TELEGRAM_CHAT_ID = -1001003794190290
```

Замени на свои значения.

### Реквизиты платежей

В `app.py`:

```python
DC_NEXT_ACCOUNT = '1234567890'      # Твой счёт DC Next
ALIF_ACCOUNT = '0987654321'         # Твой счёт Alif Mobi
```

В `diamond-shop-updated.html`:

```javascript
const CONFIG = {
  BACKEND_URL: 'http://localhost:5000',  // URL твоего сервера
  DC_NEXT_ACCOUNT: '1234567890',
  ALIF_ACCOUNT: '0987654321'
};
```

## 📊 Как это работает

### Для клиента:

1. Открывает сайт
2. Выбирает пакет алмазов
3. Выбирает способ оплаты (DC Next или Alif Mobi)
4. Видит реквизиты для перевода
5. Делает платёж
6. Загружает скриншот чека
7. Отправляет заказ

### Для исполнителей (в Telegram группе):

1. Получают уведомление о новом заказе с фото чека
2. Нажимают кнопку "✅ Принять заказ"
3. Выполняют заказ (пополняют баланс игроку)
4. Нажимают "✓ Заказ выполнен"
5. Если что-то не так, нажимают "❌ Отмена" и выбирают причину

## 🔌 API Endpoints

### Отправка заказа
```
POST /api/submit-order
Content-Type: multipart/form-data

playerId: string
package: string (starter, basic, popular, advanced, pro, elite)
diamonds: string
price: string
paymentMethod: string (dc-next, alif)
receipt: file
```

### Принятие заказа
```
POST /api/accept-order
Content-Type: application/json

{
  "order_id": "ABC123",
  "executor_name": "Имя исполнителя",
  "executor_id": 123456789
}
```

### Завершение заказа
```
POST /api/complete-order
Content-Type: application/json

{
  "order_id": "ABC123"
}
```

### Отмена заказа
```
POST /api/cancel-order
Content-Type: application/json

{
  "order_id": "ABC123",
  "reason": "Причина отмены",
  "executor_name": "Имя исполнителя"
}
```

### Получение заказов
```
GET /api/orders?status=pending
GET /api/order/ABC123
```

## 📦 Развёртывание на сервер

### Вариант 1: Heroku

1. Создай аккаунт на [heroku.com](https://www.heroku.com)
2. Установи Heroku CLI
3. Создай файл `Procfile`:
```
web: python app.py
worker: python telegram_bot.py
```

4. Деплой:
```bash
heroku create diamond-shop
git push heroku main
heroku ps:scale web=1 worker=1
```

### Вариант 2: Railway

1. Создай аккаунт на [railway.app](https://railway.app)
2. Подключи свой GitHub репозиторий
3. Добавь переменные окружения:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

### Вариант 3: VPS (Ubuntu/Debian)

```bash
# Установка зависимостей
sudo apt update
sudo apt install python3-pip python3-venv

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Запуск с помощью systemd или supervisor
sudo nano /etc/systemd/system/diamond-shop.service
```

## 🔒 Безопасность

- Все файлы чеков сохраняются на сервер
- Используется CORS для защиты API
- Проверяется размер и тип файлов
- Telegram Bot Token защищён

## 📝 Логирование

Все события логируются в консоль:
- Новые заказы
- Принятие заказов
- Завершение заказов
- Отмены с причинами
- Ошибки

## 🐛 Решение проблем

### Бот не отправляет сообщения
- Проверь токен бота
- Убедись, что бот добавлен в группу
- Проверь ID группы (должен начинаться с -100)

### Файлы чеков не загружаются
- Проверь размер файла (максимум 5 МБ)
- Убедись, что папка `uploads` существует
- Проверь права доступа к папке

### Сервер не запускается
- Убедись, что порт 5000 свободен
- Проверь установку всех зависимостей
- Посмотри логи ошибок

## 📞 Поддержка

Если у тебя есть вопросы или проблемы, проверь:
1. Логи консоли
2. Конфигурацию токена и ID
3. Подключение к интернету
4. Права доступа к файлам

## 📄 Лицензия

Этот проект создан для Diamond Shop. Все права защищены.

## 🎨 Кастомизация

### Изменение цветов
В `diamond-shop-updated.html` найди переменные CSS:
```css
:root {
  --neon-violet: #a855f7;
  --neon-blue: #3b82f6;
  --neon-cyan: #06b6d4;
  /* и т.д. */
}
```

### Добавление новых пакетов
Добавь новую карточку в HTML:
```html
<div class="pkg-card" data-pkg="custom" data-price="999" data-diamonds="10000">
  <!-- содержимое -->
</div>
```

### Изменение способов оплаты
Отредактируй раздел `<!-- Способ оплаты -->` в HTML.

---

**Создано с ❤️ для Diamond Shop**

Версия: 1.0.0  
Последнее обновление: 2024
