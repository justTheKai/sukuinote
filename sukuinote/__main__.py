import asyncio
from pyrogram import idle
from . import loop, apps, slave, app_user_ids, session

async def main():
    async def _start_app(app):
        await app.start()
        asyncio.create_task(_get_me_loop(app))
    async def _get_me_loop(app):
        while True:
            try:
                me = await app.get_me()
                app_user_ids[me.id] = me
            except:
                pass
            await asyncio.sleep(60)
    await asyncio.gather(*(_start_app(app) for app in apps), slave.start())
    await idle()
    await asyncio.gather(*(app.stop() for app in apps), slave.stop())
    await session.close()

loop.run_until_complete(main())
