"""Telegram bot for Wisey — ask Thinkwise questions from your phone."""

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from wisey.agent import ask, retrieve

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WELCOME_MESSAGE = (
    "Hey! I'm Wisey, your Thinkwise knowledge assistant.\n\n"
    "Just send me a question about the Thinkwise platform and I'll search "
    "the docs, community posts, and release notes to find the answer.\n\n"
    "Examples:\n"
    "• How do I set up OpenID in IAM?\n"
    "• What changed in version 2024.2?\n"
    "• How does branching work in Software Factory?"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_MESSAGE)


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = update.message.text.strip()
    if not question:
        return

    await update.message.chat.send_action("typing")

    try:
        answer = ask(question)
        # Telegram has a 4096 char limit per message
        if len(answer) <= 4096:
            await update.message.reply_text(answer, parse_mode="Markdown")
        else:
            # Split on paragraph boundaries
            chunks = []
            current = ""
            for para in answer.split("\n\n"):
                if len(current) + len(para) + 2 > 4000:
                    chunks.append(current)
                    current = para
                else:
                    current = f"{current}\n\n{para}" if current else para
            if current:
                chunks.append(current)

            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        await update.message.reply_text(
            "Sorry, something went wrong while looking that up. Please try again."
        )


async def sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show raw source chunks for the given query."""
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Usage: /sources <your question>")
        return

    await update.message.chat.send_action("typing")

    chunks = retrieve(query, top_k=5)
    if not chunks:
        await update.message.reply_text("No relevant documents found.")
        return

    parts = []
    for i, c in enumerate(chunks, 1):
        label = c["source_type"].replace("_", " ").title()
        parts.append(f"{i}. [{label}] {c['title']} ({c['similarity']:.2f})\n{c['source_url']}")

    await update.message.reply_text("\n\n".join(parts))


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sources", sources))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))

    logger.info("Wisey Telegram bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
