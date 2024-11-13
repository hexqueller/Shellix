import os
import subprocess
from datetime import datetime
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Проверяем и создаем папку для логов, если она не существует
LOG_DIR = "/var/log/shellix"
os.makedirs(LOG_DIR, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    container_name = f"user_container_{user_id}"

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
                ["docker", "run", "-d", "--name", container_name, "ubuntu:24.04", "sleep", "infinity"]
            )
            await update.message.reply_text("Контейнер создан.")
        except subprocess.CalledProcessError:
            await update.message.reply_text("Не удалось создать контейнер.")
            return
    else:
        await update.message.reply_text("Контейнер уже существует.")

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
            ["docker", "exec", container_name, "bash", "-c", command],
            text=True,
            stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        result = f"Error:\n{e.output}"

    # Отправляем результат в формате `bash`
    await update.message.reply_text(f"```bash\n{result}\n```", parse_mode='MarkdownV2')

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

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, execute))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()