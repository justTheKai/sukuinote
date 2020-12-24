import os
import html
import asyncio
import tempfile
from decimal import Decimal
from urllib.parse import urlparse, urlunparse, quote as urlencode
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from .. import config, help_dict, log_errors, public_log_errors, session, get_file_mimetype, progress_callback

async def download_file(url, filename):
    async with session.get(url) as resp:
        if resp.status != 200:
            return False
        with open(filename, 'wb') as file:
            while True:
                chunk = await resp.content.read(4096)
                if not chunk:
                    return True
                file.write(chunk)

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['saucenao', 'sauce'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def saucenao(client, message):
    media = message.photo or message.animation or message.video or message.sticker or message.document
    if not media:
        reply = message.reply_to_message
        if not getattr(reply, 'empty', True):
            media = reply.photo or reply.animation or reply.video or reply.sticker or reply.document
    if not media:
        await message.reply_text('Photo or GIF or Video or Sticker required')
        return
    with tempfile.TemporaryDirectory() as tempdir:
        reply = await message.reply_text('Downloading...')
        filename = await client.download_media(media, file_name=os.path.join(tempdir, '0'), progress=progress_callback, progress_args=(reply, 'Downloading...', False))
        mimetype = await get_file_mimetype(filename)
        if not mimetype.startswith('image/') and not mimetype.startswith('video/'):
            await reply.edit_text('Photo or GIF or Video or Sticker required')
            return
        if mimetype.startswith('video/'):
            new_path = os.path.join(tempdir, '1.gif')
            proc = await asyncio.create_subprocess_exec('ffmpeg', '-an', '-sn', '-i', filename, new_path)
            await proc.communicate()
            filename = new_path
        with open(filename, 'rb') as file:
            async with session.post(f'https://saucenao.com/search.php?db=999&output_type=2&numres=5&api_key={urlencode(config["config"]["saucenao_api"])}', data={'file': file}) as resp:
                json = await resp.json()
        if json['header']['status']:
            await reply.edit_text(f'<b>{json["header"]["status"]}:</b> {html.escape(json["header"].get("message", "No message"))}')
            return
        minimum_similarity = Decimal(json['header']['minimum_similarity'])
        caption = text = ''
        to_image = False
        filename = os.path.join(tempdir, '0')
        for result in json['results']:
            atext = f'<b>{html.escape(result["header"]["index_name"])}'
            if Decimal(result['header']['similarity']) < minimum_similarity:
                atext += ' (low similarity result)'
            atext += '</b>'
            if result['data'].get('ext_urls'):
                atext += '\n<b>URL'
                if len(result['data']['ext_urls']) > 1:
                    atext += 's:</b>\n'
                    atext += '\n'.join(map(html.escape, result['data']['ext_urls']))
                else:
                    atext += f':</b> {html.escape(result["data"]["ext_urls"][0])}'
                if not to_image:
                    for url in result['data']['ext_urls']:
                        if await download_file(url, filename):
                            with open(filename) as file:
                                soup = BeautifulSoup(file.read())
                            pimg = soup.find(lambda tag: tag.name == 'meta' and tag.attrs.get('property') == 'og:image' and tag.attrs.get('content'))
                            if pimg:
                                pimg = pimg.attrs.get('content', '').strip()
                                if pimg:
                                    parsed = list(urlparse(pimg))
                                    if not parsed[0]:
                                        parsed[0] = 'https'
                                        pimg = urlunparse(parsed)
                                    if parsed[0] not in ('http', 'https'):
                                        continue
                                    if await download_file(pimg, filename):
                                        to_image = True
                                        break
                    else:
                        await download_file(result['header']['thumbnail'], filename)
                        to_image = True
            atext += '\n\n'
            if len((await client.parser.parse(caption + atext))['message']) <= 1024:
                caption += atext
            text += atext
        try:
            await message.reply_photo(filename, caption=caption)
        except Exception:
            await message.reply_text(text)

help_dict['saucenao'] = ('saucenao',
'''{prefix}saucenao <i>(as caption of Photo/GIF/Video/Sticker or reply)</i> - Reverse searches anime art, thanks to saucenao.com
Aliases: {prefix}sauce''')
