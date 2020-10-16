import re
import html
import asyncio
from pyrogram import Client, filters
from .. import config, help_dict, log_errors, public_log_errors

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.outgoing & filters.regex('^(?:' + '|'.join(map(re.escape, config['config']['prefixes'])) + r')(?:(?:ba)?sh|shell|term(?:inal)?)\s+(.+)(?:\n([\s\S]+))?$'))
@log_errors
@public_log_errors
async def shell(client, message):
    command = message.matches[0].group(1)
    stdin = message.matches[0].group(2)
    reply = await message.reply_text('Executing...')
    process = await asyncio.create_subprocess_shell(command, stdin=asyncio.subprocess.PIPE if stdin else None, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await process.communicate(stdin.encode() if stdin else None)
    returncode = process.returncode
    text = f'<b>Exit Code:</b> <code>{returncode}</code>\n'
    stdout = stdout.decode().replace('\r', '').strip('\n')
    stderr = stderr.decode().replace('\r', '').strip('\n')
    if stderr:
        text += f'<code>{html.escape(stderr)}</code>\n'
    if stdout:
        text += f'<code>{html.escape(stdout)}</code>'
    await reply.edit_text(text)

help_dict['shell'] = ('Shell',
'''{prefix}sh <i>&lt;command&gt;</i> \\n <i>[stdin]</i> - Executes <i>&lt;command&gt;</i> in shell
Aliases: {prefix}bash, {prefix}shell, {prefix}term, {prefix}terminal''')
