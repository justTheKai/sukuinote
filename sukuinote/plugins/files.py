import os
import html
from pyrogram import Client, filters
from pyrogram.errors.exceptions.bad_request_400 import MessageIdInvalid
from .. import config, help_dict, log_errors, session, progress_callback, public_log_errors

@Client.on_message(~filters.forwarded & ~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['ls', 'hls', 'hiddenls'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def ls(client, message):
    dir = os.path.abspath(os.path.expanduser(' '.join(message.command[1:]) or '.'))
    text = ''
    folders = []
    files = []
    try:
        for i in sorted(os.listdir(dir)):
            if i.startswith('.') and 'h' not in message.command[0]:
                continue
            (folders if os.path.isdir(os.path.join(dir, i)) else files).append(i)
    except NotADirectoryError:
        text = f'<code>{html.escape(os.path.basename(dir))}</code>'
    except BaseException as ex:
        text = f'{type(ex).__name__}: {html.escape(str(ex))}'
    else:
        for i in folders:
            text += f'<code>{html.escape(i)}</code>\n'
        for i in files:
            text += f'<code>{html.escape(i)}</code>\n'
    await message.reply_text(text or 'Empty', disable_web_page_preview=True)

@Client.on_message(~filters.forwarded & ~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['ul', 'upload'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def upload(client, message):
    file = os.path.expanduser(' '.join(message.command[1:]))
    if not file:
        return
    text = f'Uploading {html.escape(file)}...'
    reply = await message.reply_text(text)
    try:
        await client.send_document(message.chat.id, file, progress=progress_callback, progress_args=(reply, text, True), force_document=True, reply_to_message_id=None if message.chat.type in ('private', 'bot') else message.message_id)
    except MessageIdInvalid:
        await message.reply_text('Upload cancelled!')
    else:
        await reply.delete()

@Client.on_message(~filters.forwarded & ~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['dl', 'download'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def download(client, message):
    file = os.path.abspath(os.path.expanduser(' '.join(message.command[1:]) or './'))
    if os.path.isdir(file):
        file = os.path.join(file, '')
    available_media = ("audio", "document", "photo", "sticker", "animation", "video", "voice", "video_note")
    download_message = None
    for i in available_media:
        if getattr(message, i, None):
            download_message = message
            break
    else:
        reply = message.reply_to_message
        if not getattr(reply, 'empty', True):
            for i in available_media:
                if getattr(reply, i, None):
                    download_message = reply
                    break
    if download_message is None:
        await message.reply_text('Media required')
        return
    text = 'Downloading...'
    reply = await message.reply_text(text)
    try:
        file = await download_message.download(file, progress=progress_callback, progress_args=(reply, text, False))
    except MessageIdInvalid:
        await message.reply_text('Download cancelled!')
    else:
        await reply.edit_text(f'Downloaded to {html.escape(file)}')

help_dict['files'] = ('Files',
'''{prefix}ls <i>[directory]</i> - Lists files in <i>[directory]</i>
{prefix}hiddenls <i>[directory]</i> - {prefix}ls but shows hidden files
Aliases: {prefix}hls

{prefix}upload <i>&lt;file name&gt;</i> - Uploads <i>&lt;file name&gt;</i>
Aliases: {prefix}ul

{prefix}download <i>[file name]</i> <i>(as reply or caption to a file)</i> - Downloads file to <i>[file name]</i>
Aliases: {prefix}dl''')
