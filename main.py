#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters)
import logging
import os
import time

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def start(bot, update):
    update.message.reply_text("I am a bot to help you merge messages.\n"
                              "Forward a bunch of messages and send /done command when you're done.")


def forward(bot, update, chat_data):
    user_id = update.message.from_user.id
    try:
        messages = str(chat_data[user_id])

    except KeyError:
        messages = ""
    chat_data[user_id] = "{}\n".format(messages + update.message.text)


def done(bot, update, chat_data):
    user_id = update.message.from_user.id
    try:
        text = str(chat_data[user_id])
        if len(text) <= 4096:
            update.message.reply_text(text)
        else:
            messages = [text[i: i + 4096] for i in range(0, len(text), 4096)]
            for part in messages:
                update.message.reply_text(part)
                time.sleep(1)
    except KeyError:
        update.message.reply_text("Forward some messages.")
    chat_data.clear()


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def main():
    updater = Updater(os.environ.get("TOKEN"))
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("done", done, pass_chat_data=True))
    dp.add_handler(MessageHandler(Filters.forwarded, forward, pass_chat_data=True))
    dp.add_error_handler(error)
    updater.start_polling()
    logger.info("Ready to rock..!")
    updater.idle()


if __name__ == "__main__":
    main()
