import time
import html
import asyncio
from pyrogram import Client, filters
from pyrogram.parser import html as pyrogram_html
from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from .. import config, help_dict, app_user_ids, log_errors

@Client.on_inline_query(filters.regex('^help$'))
@log_errors
async def main_help(client, inline_query):
    if inline_query.from_user.id not in app_user_ids:
        await inline_query.answer([
            InlineQueryResultArticle('...no', InputTextMessageContent('...no'))
        ], cache_time=3600, is_personal=True)
        return
    buttons = []
    to_append = []
    prefixes = config['config']['prefixes'] or []
    if not isinstance(prefixes, list):
        prefixes = prefixes.split()
    prefixes = ', '.join(prefixes)
    prefix = prefixes[0]
    results = []
    parser = pyrogram_html.HTML(client)
    me = None
    for internal_name in sorted(help_dict):
        external_name, help_text = help_dict[internal_name]
        if '{bot}' in help_text:
            if not me:
                me = await client.get_me()
        text = f'Help for {html.escape(external_name)}:\nAvaliable prefixes: {prefixes}\n\n{help_text.format(prefix=prefix, bot=getattr(me, "username", None))}'
        to_append.append(InlineKeyboardButton(external_name, f'help_m{internal_name}'))
        if len(to_append) > 2:
            buttons.append(to_append)
            to_append = []
        results.append(InlineQueryResultArticle(external_name, InputTextMessageContent(text), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Back', 'help_back')]]), description=(await parser.parse(help_text.format(prefix=prefix, bot=getattr(me, 'username', None))))['message'], id=f'helpm{internal_name}-{time.time()}'))
    else:
        if to_append:
            buttons.append(to_append)
    results.insert(0, InlineQueryResultArticle('Main Menu', InputTextMessageContent('Select the plugin you want help with'), reply_markup=InlineKeyboardMarkup(buttons), id=f'helpa-{time.time()}'))
    await inline_query.answer(results, is_personal=True)

message_info = dict()
lock = asyncio.Lock()
@Client.on_chosen_inline_result()
@log_errors
async def help_chosen(client, inline_result):
    if inline_result.query == 'help':
        if inline_result.result_id.startswith('helpm'):
            location = inline_result.result_id[5:].split('-')
            location.pop()
            message_info[inline_result.inline_message_id] = '-'.join(location)
            return
        elif inline_result.result_id.startswith('helpa'):
            message_info[inline_result.inline_message_id] = None
            return
    inline_result.continue_propagation()

@Client.on_callback_query(filters.regex('^help_back$'))
@log_errors
async def help_back(client, callback_query):
    if callback_query.from_user.id not in app_user_ids:
        await callback_query.answer('...no', cache_time=3600, show_alert=True)
        return
    message_identifier = callback_query.inline_message_id
    async with lock:
        if message_info.get(message_identifier, True):
            buttons = []
            to_append = []
            for internal_name in sorted(help_dict):
                external_name, _ = help_dict[internal_name]
                to_append.append(InlineKeyboardButton(external_name, f'help_m{internal_name}'))
                if len(to_append) > 2:
                    buttons.append(to_append)
                    to_append = []
            if to_append:
                buttons.append(to_append)
            await callback_query.edit_message_text('Select the plugin you want help with', reply_markup=InlineKeyboardMarkup(buttons))
            message_info[message_identifier] = None
    await callback_query.answer()

@Client.on_callback_query(filters.regex('^help_m(.+)$'))
@log_errors
async def help_m(client, callback_query):
    if callback_query.from_user.id not in app_user_ids:
        await callback_query.answer('...no', cache_time=3600, show_alert=True)
        return
    message_identifier = callback_query.inline_message_id
    plugin = callback_query.matches[0].group(1)
    async with lock:
        if message_info.get(message_identifier) != plugin:
            if plugin not in help_dict:
                await callback_query.answer('What plugin?', cache_time=3600, show_alert=True)
                return
            external_name, help_text = help_dict[plugin]
            prefixes = config['config']['prefixes'] or []
            if not isinstance(prefixes, list):
                prefixes = prefixes.split()
            prefixes = ', '.join(prefixes)
            text = f'Help for {html.escape(external_name)}:\n'
            prefix = ''
            if prefixes:
                text += f'Avaliable prefixes: {prefixes}\n'
                prefix = prefixes[0]
            me = None
            if '{bot}' in help_text:
                me = await client.get_me()
            text += f'\n{help_text.format(prefix=prefix, bot=getattr(me, "username", None))}'
            await callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Back', 'help_back')]]))
            message_info[message_identifier] = plugin
    await callback_query.answer()
