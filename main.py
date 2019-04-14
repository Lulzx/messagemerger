#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging
import os

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def start(bot, update):
    update.message.reply_text("""I am a bot to help you merge messages.""")
    update.message.reply_text("""Forward a bunch of messages and send /done command when you're done, I will send you an always-at-the-bottom message with all contents concatenated!""")


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
        messages = chat_data[user_id]
        update.message.reply_text(messages)

    except KeyError:
        update.message.reply_text('Forward some messages.')
    chat_data.clear()


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    TOKEN = os.environ.get('TOKEN')
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("done", done, pass_chat_data=True))
    dp.add_handler(MessageHandler(Filters.forwarded, forward, pass_chat_data=True))
    dp.add_error_handler(error)
    PORT = int(os.environ.get('PORT', '8443'))
    updater.start_webhook(listen="0.0.0.0",
                      port=PORT,
                      url_path=TOKEN)
    updater.bot.set_webhook("https://lulzx.herokuapp.com/" + TOKEN)
    logger.info("Ready to rock..!")
    updater.idle()


if __name__ == '__main__':
    main()
