import re
import time
import asyncio
from urllib.parse import quote as urlencode
from pyrogram import Client, filters
from pyrogram.parser.html import HTML as pyrogram_html
from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from .. import session, app_user_ids, log_errors

all_results = dict()
results_lock = asyncio.Lock()
@Client.on_inline_query(filters.regex('^w(?:iki)?(?:pedia)?(.+)$'))
@log_errors
async def wikipedia(client, inline_query):
    if inline_query.from_user.id not in app_user_ids:
        await inline_query.answer([
            InlineQueryResultArticle('...no', InputTextMessageContent('...no'))
        ], cache_time=3600, is_personal=True)
        return
    query = inline_query.matches[0].group(1).strip().lower()
    async with results_lock:
        if query not in all_results:
            async with session.get(f'https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&formatversion=2&srlimit=10&srprop=snippet&srenablerewrites=1&srsearch={urlencode(query)}') as resp:
                all_results[query] = (await resp.json())['query']['search']
    results = all_results[query]
    answers = []
    parser = pyrogram_html(client)
    for a, result in enumerate(results):
        full_snippet = None
        text = f'<a href="https://en.wikipedia.org/wiki/{urlencode(result["title"])}">{result["title"]}</a>\n\n'
        if result['snippet']:
            full_snippet = snippet = (await parser.parse(result['snippet']))['message']
            total_length = len((await parser.parse(text))['message'])
            if len(snippet) > 1022 - total_length:
                snippet = snippet[:1021-total_length] + '…'
            text += snippet
        buttons = [InlineKeyboardButton('Back', 'wikipedia_back'), InlineKeyboardButton(f'{a + 1}/{len(results)}', 'wikipedia_nop'), InlineKeyboardButton('Next', 'wikipedia_next')]
        if not a:
            buttons.pop(0)
        if len(results) == a + 1:
            buttons.pop()
        answers.append(InlineQueryResultArticle(result['title'], InputTextMessageContent(text, disable_web_page_preview=True), reply_markup=InlineKeyboardMarkup([buttons]), id=f'wikipedia{a}-{time.time()}', description=full_snippet))
    await inline_query.answer(answers, is_personal=True)

@Client.on_callback_query(filters.regex('^wikipedia_nop$'))
@log_errors
async def wikipedia_nop(client, callback_query):
    await callback_query.answer(cache_time=3600)

message_info = dict()
message_lock = asyncio.Lock()
@Client.on_chosen_inline_result()
@log_errors
async def wikipedia_chosen(client, inline_result):
    if inline_result.result_id.startswith('wikipedia'):
        match = re.match('^w(?:iki)?(?:pedia)?(.*)$', inline_result.query)
        if match:
            query = match.group(1).strip().lower()
            if query:
                page = int(inline_result.result_id[9])
                message_info[inline_result.inline_message_id] = query, page
                async with results_lock:
                    if query not in all_results:
                        async with session.get(f'https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&formatversion=2&srlimit=10&srprop=snippet&srenablerewrites=1&srsearch={urlencode(query)}') as resp:
                            all_results[query] = (await resp.json())['query']['search']
                return
    inline_result.continue_propagation()

@Client.on_callback_query(filters.regex('^wikipedia_(back|next)$'))
@log_errors
async def wikipedia_move(client, callback_query):
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
            async with results_lock:
                results = all_results[query]
            result = results[page]
            text = f'<a href="https://en.wikipedia.org/wiki/{urlencode(result["title"])}">{result["title"]}</a>\n\n'
            if result['snippet']:
                parser = pyrogram_html(client)
                snippet = (await parser.parse(result['snippet']))['message']
                total_length = len((await parser.parse(text))['message'])
                if len(snippet) > 1022 - total_length:
                    snippet = snippet[:1021-total_length] + '…'
                text += snippet
            buttons = [InlineKeyboardButton('Back', 'wikipedia_back'), InlineKeyboardButton(f'{page + 1}/{len(results)}', 'wikipedia_nop'), InlineKeyboardButton('Next', 'wikipedia_next')]
            if not page:
                buttons.pop(0)
            if len(results) == page + 1:
                buttons.pop()
            await callback_query.edit_message_text(text, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([buttons]))
            message_info[callback_query.inline_message_id] = query, page
    await callback_query.answer()
