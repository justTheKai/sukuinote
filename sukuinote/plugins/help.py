import html
from pyrogram import Client, filters
from pyrogram.errors.exceptions.forbidden_403 import Forbidden
from .. import slave, config, help_dict, log_errors, public_log_errors

@Client.on_message(~filters.forwarded & ~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command('help', prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def help(client, message):
    bot = await slave.get_me()
    module = message.command
    module.pop(0)
    module = ' '.join(module).lower().strip()
    results = await client.get_inline_bot_results(bot.username or bot.id, 'help')
    for a, i in enumerate(results.results):
        if a:
            internal_name = i.id[5:].split('-')
            internal_name.pop()
            internal_name = '-'.join(internal_name).lower().strip()
            external_name = i.title.lower().strip()
            if module in (internal_name, external_name):
                result = i
                break
    else:
        result = results.results[0]
    try:
        await message.reply_inline_bot_result(results.query_id, result.id)
    except Forbidden:
        if module:
            await message.reply_text({'message': result.send_message.message, 'entities': result.send_message.entities}, parse_mode='through')
        else:
            text = 'Avaliable plugins:\n'
            for i in sorted(help_dict):
                text += f'- {html.escape(help_dict[i][0])}\n'
            await message.reply_text(text)

help_dict['help'] = ('Help',
'''{prefix}help - Shows list of plugins
{prefix}help <i>&lt;plugin name&gt;</i> - Shows help for <i>&lt;plugin name&gt;</i>
Can also be activated inline with: @{bot} help''')
