#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This module contains functions for handling errors."""
import html
import logging
import traceback

from emoji import emojize
from telegram import Update
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html

from bot import ADMIN_KEY

logger = logging.getLogger(__name__)


def handle_error(update: Update, context: CallbackContext) -> None:
    """
    Informs the originator of the update that an error occurred and forwards the traceback to the
    admin.

    Args:
        update: The Telegram update.
        context: The callback context as provided by the dispatcher.
    """
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # Inform sender of update, that something went wrong
    if update.effective_message:
        text = emojize(
            'Huch, da ist etwas schief gelaufen :worried:. Ich melde es dem Hirsch :nerd_face:.',
            use_aliases=True)
        update.effective_message.reply_text(text)

    # Get traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    trace = ''.join(tb_list)

    # Gather information from the update
    payload = ''
    if update.effective_user:
        payload += ' with the user {}'.format(
            mention_html(update.effective_user.id, update.effective_user.first_name))
    if update.effective_chat.username:
        payload += f' (@{html.escape(update.effective_chat.username)})'
    if update.poll:
        payload += f' with the poll id {update.poll.id}.'
    text = f'Hey.\nThe error <code>{html.escape(str(context.error))}</code> happened' \
           f'{payload}. The full traceback:\n\n<code>{html.escape(trace)}</code>'

    # Send to admin
    context.bot.send_message(context.bot_data[ADMIN_KEY], text)
