import os
import logging
import requests
from pyrogram import Client, filters
from pyrogram.types import InputTextMessageContent, InlineQueryResultArticle, InlineQueryResultPhoto, InlineQueryResultAnimation
from .. import log_errors, session, app_user_ids

def _generate(i):
    @Client.on_inline_query(filters.regex(f'^{i}$'))
    @log_errors
    async def func(client, inline_query):
        if inline_query.from_user.id not in app_user_ids:
            await inline_query.answer([InlineQueryResultArticle('...no', InputTextMessageContent('...no'))], cache_time=3600, is_personal=True)
            return
        async with session.get(f'https://nekos.life/api/v2/img/{i}') as resp:
            url = (await resp.json())['url']
        call = InlineQueryResultAnimation if '.gif' == os.path.splitext(url)[1] else InlineQueryResultPhoto
        await inline_query.answer([call(url, caption=url, parse_mode=None)], cache_time=0)
    return func

try:
    resp = requests.get('https://nekos.life/api/v2/endpoints')
    json = resp.json()
except BaseException:
    logging.exception('Cannot connect to nekos.life')
else:
    for i in json:
        _, i = i.split(' ', 1)
        i = i.strip()
        if i.startswith('/api/v2/img/<\''):
            for i in os.path.basename(i)[1:-1].split(', '):
                i = i[1:-1]
                if 'v3' in i:
                    continue
                func = _generate(i)
                globals()[i] = func
                locals()[i] = func
                func = None
            break
