"""
new Env('京东cookie强制作废');
cron: 1 1 * * * jd_cookie_kill.py
"""
import asyncio
import logging

from qinglong import init_ql
from utils import get_cookies

logger = logging.getLogger(__name__)

try:
    from notify import send
except:
    send = lambda *args: ...


async def main():
    ql = init_ql()
    cookies = await get_cookies(ql)

    disable_cookies_ids = [x['id'] for x in cookies]
    ql.disable_env(disable_cookies_ids)


    msg = "\n".join(
        [
            f"{cookie['remarks'].split('@')[0]} cookie 作废成功"
            for cookie in cookies
        ]
    )
    send("京东cookie强制失效", msg)



if __name__ == "__main__":
    asyncio.run(main())
