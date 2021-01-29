import os
import logging
import requests
from pyrogram import Client, filters
from pyrogram.types.messages_and_media import Photo, Animation
from pyrogram.errors.exceptions.forbidden_403 import Forbidden
from .. import config, help_dict, log_errors, session, slave, public_log_errors

help_text = ''

def _generate(i):
    @Client.on_message(~filters.forwarded & ~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(i, prefixes=config['config']['prefixes']))
    @log_errors
    @public_log_errors
    async def func(client, message):
        bot = await slave.get_me()
        results = await client.get_inline_bot_results(bot.username or bot.id, i)
        result = results.results[0]
        to_reply = message
        if not getattr(message.reply_to_message, 'empty', True):
            to_reply = message.reply_to_message
        if result.type == 'photo':
            file = Photo._parse(client, result.photo)
        else:
            file = Animation._parse(client, result.document, result.document.attributes, 'hello.mp4')
        try:
            await to_reply.reply_cached_media(file.file_id, caption=result.send_message.message, parse_mode=None)
        except Forbidden:
            await to_reply.reply_text(result.send_message.message, parse_mode=None)
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
                help_text += '{prefix}' + i.lower() + f' - Gets a {"gif" if "gif" in i else "picture"} of {i.lower()}\n'
            break
    help_dict['nekos'] = ('Nekos.life', help_text + '\nCan also be activated inline with: @{bot} <i>&lt;command without prefix&gt;</i>')
