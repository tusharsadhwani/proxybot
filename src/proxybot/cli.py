"""CLI interface for proxybot."""
from __future__ import annotations

import logging

from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    MessageReactionHandler,
    filters,
)

from proxybot.db import setup_db, get_db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

MASTER_CHAT_ID: int = 0  # Put your master chat id here
BOT_TOKEN = "TOKEN"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None

    user = update.effective_user
    assert user is not None

    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    assert message is not None
    await message.reply_text("Help!")


async def forward_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_reaction = update.message_reaction
    assert message_reaction is not None

    db = get_db()
    chat_id = message_reaction.chat.id
    assert chat_id == MASTER_CHAT_ID

    message_id = message_reaction.message_id
    query = db.cursor().execute(
        "select user_id, dm_message_id from forwards where message_id = ?",
        (message_id,),
    )
    message_data = query.fetchone()
    if message_data is None:
        # The liked message was not forwarded from a DM.
        return
    
    user_id, dm_message_id = message_data
    await context.bot.set_message_reaction(
        user_id, dm_message_id, message_reaction.new_reaction
    )


async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    assert message is not None
    if message.text is None:
        return

    db = get_db()
    chat_id = message.chat.id
    reply_to = message.reply_to_message

    if (
        chat_id == MASTER_CHAT_ID
        and reply_to is not None
        and reply_to.from_user is not None
        and reply_to.from_user.id == context.bot.id
    ):
        query = db.cursor().execute(
            "SELECT user_id, dm_message_id FROM forwards WHERE message_id = ?",
            (reply_to.id,),
        )
        user_id, dm_message_id = query.fetchone()
        await context.bot.send_message(
            user_id, message.text, reply_to_message_id=dm_message_id
        )

    elif chat_id > 0:
        forwarded_message = await message.forward(MASTER_CHAT_ID)
        db.cursor().execute(
            "INSERT INTO forwards VALUES (?, ?, ?)",
            (forwarded_message.id, chat_id, message.id),
        )
        db.commit()


def cli() -> int:
    if MASTER_CHAT_ID == 0:
        print("\033[1;31mError:\033[m Please set MASTER_CHAT_ID and BOT_TOKEN in `cli.py`.")
        return 1

    setup_db()

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward))
    application.add_handler(
        MessageReactionHandler(forward_reaction, chat_id=MASTER_CHAT_ID)
    )

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    return 0
