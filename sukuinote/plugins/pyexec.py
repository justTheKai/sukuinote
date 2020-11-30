# https://greentreesnakes.readthedocs.io/
import re
import ast
import sys
import html
import inspect
import asyncio
from io import StringIO, BytesIO
from pyrogram import Client, filters
from .. import config, help_dict, log_errors, slave, apps, session, public_log_errors

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.regex('^(?:' + '|'.join(map(re.escape, config['config']['prefixes'])) + r')exec\s+([\s\S]+)$'))
@log_errors
@public_log_errors
async def pyexec(client, message):
    code = message.matches[0].group(1).strip()
    class UniqueExecReturnIdentifier:
        pass
    tree = ast.parse(code)
    obody = tree.body
    body = obody.copy()
    body.append(ast.Return(ast.Name('_ueri', ast.Load())))
    def _gf(body):
        # args: c, client, m, message, executing, r, reply, _ueri
        func = ast.AsyncFunctionDef('ex', ast.arguments([], [ast.arg(i, None, None) for i in ['c', 'client', 'm', 'message', 'executing', 'r', 'reply', '_ueri']], None, [], [], None, []), body, [], None, None)
        ast.fix_missing_locations(func)
        mod = ast.parse('')
        mod.body = [func]
        fl = locals().copy()
        exec(compile(mod, '<ast>', 'exec'), globals(), fl)
        return fl['ex']
    try:
        exx = _gf(body)
    except SyntaxError as ex:
        if ex.msg != "'return' with value in async generator":
            raise
        exx = _gf(obody)
    reply = await message.reply_text('Executing...')
    async_obj = exx(client, client, message, message, reply, message.reply_to_message, message.reply_to_message, UniqueExecReturnIdentifier)
    stdout = sys.stdout
    stderr = sys.stderr
    wrapped_stdout = StringIO()
    wrapped_stderr = StringIO()
    try:
        sys.stdout = wrapped_stdout
        sys.stderr = wrapped_stderr
        if inspect.isasyncgen(async_obj):
            returned = [i async for i in async_obj]
        else:
            returned = [await async_obj]
            if returned == [UniqueExecReturnIdentifier]:
                returned = []
    finally:
        sys.stdout = stdout
        sys.stderr = stderr
    wrapped_stderr.seek(0)
    wrapped_stdout.seek(0)
    output = ''
    wrapped_stderr_text = wrapped_stderr.read().strip()
    wrapped_stdout_text = wrapped_stdout.read().strip()
    if wrapped_stderr_text:
        output += f'<code>{html.escape(wrapped_stderr_text)}</code>\n'
    if wrapped_stdout_text:
        output += f'<code>{html.escape(wrapped_stdout_text)}</code>\n'
    for i in returned:
        output += f'<code>{html.escape(str(i).strip())}</code>\n'
    if not output.strip():
        output = 'Executed'
    
    # send as a file if it's longer than 4096 bytes
    if len(output) > 4096:
        out = wrapped_stderr_text + "\n" + wrapped_stdout_text + "\n"
        for i in returned:
            out += str(i).strip() + "\n"
        f = BytesIO(out.strip().encode('utf-8'))
        f.name = "output.txt"
        await reply.delete()
        await message.reply_document(f)
    else:
        await reply.edit_text(output)

help_dict['exec'] = ('Exec', '{prefix}exec <i>&lt;python code&gt;</i> - Executes python code')
