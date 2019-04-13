#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging
import os

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

user_data = dict()


def start(bot, update):
    update.message.reply_text("""I am a bot to help you merge messages.""")
    update.message.reply_text("""Forward a bunch of messages and send /done command when you're done, I will send you an always-at-the-bottom message with all contents concatenated!""")


def forward(bot, update):
    global user_data
    user_id = update.message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = dict()
    message = str(user_data[user_id]) + update.message.text
    temp = {user_id: "{}\n".format(message)}
    user_data.update(temp)


def delete(user_id):
    global user_data
    del user_data[user_id]


def done(bot, update):
    user_id = update.message.from_user.id
    text = user_data[user_id]
    update.message.reply_text(text[2:])
    delete(user_id)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    updater = Updater(os.environ.get('TOKEN'))
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("done", done))
    dp.add_handler(MessageHandler(Filters.forwarded, forward))
    dp.add_error_handler(error)
    updater.start_polling()
    logger.info("Ready to rock..!")
    updater.idle()


if __name__ == '__main__':
    main()
