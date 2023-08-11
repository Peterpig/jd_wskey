"""
new Env('京东cookie失效检测');
cron: 30 * * * * jd_cookie_observe.py
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

    disable_cookies = list(filter(lambda x: x["status"] != 0, cookies))
    if disable_cookies:
        msg = "\n".join(
            [
                f"{cookie['remarks'].split('@')[0]} cookie失效"
                for cookie in disable_cookies
            ]
        )
        send("京东cookie失效", msg)


if __name__ == "__main__":
    asyncio.run(main())
