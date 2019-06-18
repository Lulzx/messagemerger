#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import sys
import time
import json
from uuid import uuid4

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (Updater, CommandHandler, InlineQueryHandler, MessageHandler, Filters)
from tinydb import TinyDB, Query

try:
    db = TinyDB('db.json')
except PermissionError:
    db = TinyDB('C:/Users/Lulzx/My Documents/msg/db.json')
user = Query()

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


def inline(bot, update, switch_pm=None):
    query = update.inline_query.query
    if not switch_pm:
        switch_pm = ['Switch to PM', 'help']
    try:
        search = db.get(user['message_id'] == f'{query}')
        json_str = json.dumps(search)
        resp = json.loads(json_str)
        text = resp['text']
        if search is None:
            text = "Go to private"
        result = [
            InlineQueryResultArticle(
                id=uuid4(),
                title="Your message",
                description="Click here to send in this chat",
                input_message_content=InputTextMessageContent(
                    "{}".format(text)))]
        update.inline_query.answer(result, switch_pm_text=f'{switch_pm[0]}', switch_pm_parameter=f'{switch_pm[1]}')
    except IndexError:
        pass


def done(bot, update, chat_data):
    user_id = update.message.from_user.id
    try:
        text = str(chat_data[user_id])
        message_id = uuid4()
        db.insert({'message_id': f'{message_id}', 'text': f'{text}'})
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("share", switch_inline_query=f'{message_id}')]])
        if len(text) <= 4096:
            update.message.reply_text(text, reply_markup=markup)
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
    try:
        token = sys.argv[1]
    except IndexError:
        token = os.environ.get("TOKEN")
    updater = Updater(token)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(InlineQueryHandler(inline))
    dp.add_handler(CommandHandler("done", done, pass_chat_data=True))
    dp.add_handler(MessageHandler(Filters.forwarded, forward, pass_chat_data=True))
    dp.add_error_handler(error)
    updater.start_polling()
    logger.info("Ready to rock..!")
    updater.idle()


if __name__ == "__main__":
    main()
