import os
import subprocess
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check if user's container exists; create it if not."""
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
    """Execute shell command in the user's container and return the result."""
    user_id = update.effective_user.id
    container_name = f"user_container_{user_id}"
    command = update.message.text  # Получаем текст команды от пользователя

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
        # В случае ошибки возвращаем её
        result = f"Error:\n{e.output}"

    # Отправляем результат в формате `bash`
    await update.message.reply_text(f"```bash\n{result}\n```", parse_mode='MarkdownV2')

def main() -> None:
    bot_token = os.getenv("TOKEN")
    if not bot_token:
        print("Token not found")
        exit(1)

    # Start the bot
    application = Application.builder().token(bot_token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))

    # on non-command message - execute as shell command
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, execute))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()