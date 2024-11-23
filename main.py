import os
import subprocess
import re
from datetime import datetime
from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# Максимально допустимая длина сообщения Telegram
MAX_MESSAGE_LENGTH = 4096

# Проверяем и создаем папку для логов, если она не существует
LOG_DIR = "/var/log/shellix"
os.makedirs(LOG_DIR, exist_ok=True)

DISTRIBUTIONS = {
    "Ubuntu": "ubuntu:24.04",
    "Arch": "archlinux:base-20241110.0.278197",
    "Alpine": "alpine:3.20"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton(distro, callback_data=container) for distro, container in DISTRIBUTIONS.items()]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Выберите дистрибутив для создания контейнера:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    container_name = f"user_container_{user_id}"
    container_image = query.data

    # Проверяем, существует ли контейнер
    container_exists = subprocess.call(
        ["docker", "inspect", container_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ) == 0

    if not container_exists:
        # Создаем контейнер, если он не существует
        try:
            subprocess.check_call(
                ["docker", "run", "-d", "--name", container_name, container_image, "sleep", "infinity"]
            )
            await query.edit_message_text(text=f"Контейнер {container_image} создан!")
        except subprocess.CalledProcessError:
            await query.edit_message_text(text="Не удалось создать контейнер.")
            return
    else:
        await query.edit_message_text(text="Контейнер уже существует.")

async def destroy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    container_name = f"user_container_{user_id}"

    # Проверяем, существует ли контейнер
    container_exists = subprocess.call(
        ["docker", "inspect", container_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ) == 0

    if container_exists:
        # Удаляем контейнер
        try:
            subprocess.check_call(
                ["docker", "rm", "-f", container_name]
            )
            await update.message.reply_text("Контейнер удален.")
        except subprocess.CalledProcessError:
            await update.message.reply_text("Не удалось удалить контейнер.")
    else:
        await update.message.reply_text("Контейнер не существует.")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    container_name = f"user_container_{user_id}"

    # Проверяем, существует ли контейнер
    container_exists = subprocess.call(
        ["docker", "inspect", container_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ) == 0

    if container_exists:
        # Перезапускаем контейнер
        try:
            subprocess.check_call(
                ["docker", "restart", container_name]
            )
            await update.message.reply_text("Контейнер перезапущен!")
        except subprocess.CalledProcessError:
            await update.message.reply_text("Не удалось перезапустить контейнер.")
    else:
        await update.message.reply_text("Контейнер не существует.")

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    container_name = f"user_container_{user_id}"
    message_text = update.message.text

    # Проверяем, существует ли контейнер
    container_exists = subprocess.call(
        ["docker", "inspect", container_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ) == 0

    if not container_exists:
        await update.message.reply_text("Контейнер не существует. Введите /start для его создания.")
        return

    # Проверяем, указан ли путь к файлу
    parts = message_text.split(" ", 1)
    if len(parts) < 2:
        await update.message.reply_text("Укажите путь к файлу после команды /download")
        return

    file_path = parts[1]

    try:
        # Скачиваем файл из контейнера
        file_data = subprocess.check_output(
            ["docker", "exec", container_name, "cat", file_path],
            text=False
        )
    except subprocess.CalledProcessError as e:
        await update.message.reply_text(f"Ошибка скачивания файла: {e.output}")
        return

    # Отправляем файл в чат
    await update.message.reply_document(document=file_data, filename=os.path.basename(file_path))

async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    container_name = f"user_container_{user_id}"
    command = update.message.text  # Получаем текст команды от пользователя

    # Логирование запроса
    log_request(user_id, command)

    # Проверяем, существует ли контейнер
    container_exists = subprocess.call(
        ["docker", "inspect", container_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ) == 0

    if not container_exists:
        await update.message.reply_text("Контейнер не существует. Введите /start для его создания.")
        return

    try:
        # Выполняем команду в контейнере
        result = subprocess.check_output(
            ["docker", "exec", container_name, "sh", "-c", command],
            text=True,
            stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        result = f"Error:\n{e.output}"

    # Проверка на telegram.error.BadRequest: Text must be non-empty
    if not result.strip():
        result = "Пустой ответ"

    # Проверка на telegram.error.BadRequest: Text is too long
    if len(result) > MAX_MESSAGE_LENGTH:
        result = "... Message is too long\n" + result[-(MAX_MESSAGE_LENGTH - 23):]

    # Экранирование зарезервированных символов
    result = re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', result)

    # Отправляем результат в формате `bash`
    await update.message.reply_text(f"```bash\n{result}\n```", parse_mode='MarkdownV2')

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Доступные команды:\n"
        "/start - Создать контейнер.\n"
        "/destroy - Удалить контейнер.\n"
        "/restart - Перезапустить контейнер.\n"
        "/download <путь к файлу> - Скачать файл из контейнера."
    )
    await update.message.reply_text(text)

def log_request(user_id: int, command: str) -> None:
    log_file = os.path.join(LOG_DIR, f"user_{user_id}.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {command}\n")

def main() -> None:
    # Забираем из системы токен
    bot_token = os.getenv("TOKEN")
    if not bot_token:
        print("Token not found")
        exit(1)

    application = Application.builder().token(bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("destroy", destroy))
    application.add_handler(CommandHandler("restart", restart))
    application.add_handler(CommandHandler("download", download))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, execute))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
