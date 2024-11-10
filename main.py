import os
import subprocess
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute shell command and return the result."""
    command = update.message.text  # Получаем текст команды от пользователя

    try:
        # Выполняем команду и захватываем вывод
        result = subprocess.check_output(command, shell=True, text=True, stderr=subprocess.STDOUT)
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