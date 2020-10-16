import html
from pyrogram import Client, filters
from pyrogram.errors.exceptions.forbidden_403 import Forbidden
from .. import slave, config, help_dict, log_errors, public_log_errors

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.outgoing & filters.command(['ud', 'urbandictionary'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def ud(client, message):
    bot = await slave.get_me()
    query = message.command
    page = 1
    query.pop(0)
    if query and query[0].isnumeric():
        page = int(query.pop(0))
    page -= 1
    if page < 0:
        page = 0
    elif page > 9:
        page = 9
    query = ' '.join(query)
    if not query:
        return
    results = await client.get_inline_bot_results(bot.username or bot.id, 'ud' + query)
    if not results.results:
        await message.reply_text('There are no definitions')
        return
    try:
        await message.reply_inline_bot_result(results.query_id, results.results[page].id)
    except IndexError:
        await message.reply_text(f'There are only {len(results.results)} definitions')
    except Forbidden:
        await message.reply_text({'message': results.results[page].send_message.message, 'entities': results.results[page].send_message.entities}, disable_web_page_preview=True, parse_mode='through')

help_dict['ud'] = ('Urban Dictionary',
'''{prefix}urbandictionary <i>&lt;query&gt;</i> - Gets the definition of <i>&lt;query&gt;</i> via Urban Dictionary
Aliases: {prefix}ud
Can also be activated inline with: @{bot} urbandictionary <i>&lt;query&gt;</i> or @{bot} ud <i>&lt;query&gt;</i>''')
