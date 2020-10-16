import re
import time
import html
import asyncio
from urllib.parse import quote as urlencode
from pyrogram import Client, filters
from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from .. import session, app_user_ids, log_errors

all_definitions = dict()
definitions_lock = asyncio.Lock()
@Client.on_inline_query(filters.regex('^u(?:rban)?d(?:ictionary)?(.+)$'))
@log_errors
async def ud(client, inline_query):
    if inline_query.from_user.id not in app_user_ids:
        await inline_query.answer([
            InlineQueryResultArticle('...no', InputTextMessageContent('...no'))
        ], cache_time=3600, is_personal=True)
        return
    query = inline_query.matches[0].group(1).strip().lower()
    async with definitions_lock:
        if query not in all_definitions:
            async with session.get(f'https://api.urbandictionary.com/v0/define?term={urlencode(query)}') as resp:
                all_definitions[query] = (await resp.json())['list']
    definitions = all_definitions[query]
    answers = []
    for a, definition in enumerate(definitions):
        text = f'''<a href="{definition["permalink"]}">{html.escape(definition["word"])}</a>
<b>Definition:</b>
{html.escape(definition["definition"])}'''
        if definition['example']:
            text += f'\n<b>Examples:</b>\n{html.escape(definition["example"])}'
        buttons = [InlineKeyboardButton('Back', 'ud_back'), InlineKeyboardButton(f'{a + 1}/{len(definitions)}', 'ud_nop'), InlineKeyboardButton('Next', 'ud_next')]
        if not a:
            buttons.pop(0)
        if len(definitions) == a + 1:
            buttons.pop()
        answers.append(InlineQueryResultArticle(definition['word'], InputTextMessageContent(text, disable_web_page_preview=True), reply_markup=InlineKeyboardMarkup([buttons]), id=f'ud{a}-{time.time()}', description=definition['definition']))
    await inline_query.answer(answers, is_personal=True)

@Client.on_callback_query(filters.regex('^ud_nop$'))
@log_errors
async def ud_nop(client, callback_query):
    await callback_query.answer(cache_time=3600)

message_info = dict()
message_lock = asyncio.Lock()
@Client.on_chosen_inline_result()
@log_errors
async def ud_chosen(client, inline_result):
    if inline_result.result_id.startswith('ud'):
        match = re.match('^u(?:rban)?d(?:dictionary)?(.*)$', inline_result.query)
        if match:
            query = match.group(1).strip().lower()
            if query:
                page = int(inline_result.result_id[2])
                message_info[inline_result.inline_message_id] = query, page
                async with definitions_lock:
                    if query not in all_definitions:
                        async with session.get(f'https://api.urbandictionary.com/v0/define?term={urlencode(query)}') as resp:
                            all_definitions[query] = (await resp.json())['list']
                return
    inline_result.continue_propagation()

@Client.on_callback_query(filters.regex('^ud_(back|next)$'))
@log_errors
async def ud_move(client, callback_query):
    if callback_query.from_user.id not in app_user_ids:
        await callback_query.answer('...no', cache_time=3600, show_alert=True)
        return
    async with message_lock:
        if callback_query.inline_message_id not in message_info:
            await callback_query.answer('This message is too old', cache_time=3600, show_alert=True)
            return
        query, page = message_info[callback_query.inline_message_id]
        opage = page
        if callback_query.matches[0].group(1) == 'back':
            page -= 1
        elif callback_query.matches[0].group(1) == 'next':
            page += 1
        if page < 0:
            page = 0
        elif page > 9:
            page = 9
        if page != opage:
            async with definitions_lock:
                definitions = all_definitions[query]
            definition = definitions[page]
            text = f'''<a href="{definition["permalink"]}">{html.escape(definition["word"])}</a>
<b>Definition:</b>
{html.escape(definition["definition"])}'''
            if definition['example']:
                text += f'\n<b>Examples:</b>\n{html.escape(definition["example"])}'
            buttons = [InlineKeyboardButton('Back', 'ud_back'), InlineKeyboardButton(f'{page + 1}/{len(definitions)}', 'ud_nop'), InlineKeyboardButton('Next', 'ud_next')]
            if not page:
                buttons.pop(0)
            if len(definitions) == page + 1:
                buttons.pop()
            await callback_query.edit_message_text(text, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([buttons]))
            message_info[callback_query.inline_message_id] = query, page
    await callback_query.answer()
