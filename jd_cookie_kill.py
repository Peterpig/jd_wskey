"""
new Env('京东cookie强制作废');
cron: 20/* * * * * jd_cookie_kill.py
"""
import random
import requests
import asyncio
import logging

from qinglong import init_ql
from utils.utils import get_cookies

logger = logging.getLogger(__name__)

try:
    from notify import send
except:
    send = lambda *args: ...


async def need_login(
        cookie: str
):
    """
    检测JD_COOKIE是否失效

    :param cookie: 就是cookie
    """
    url = "https://me-api.jd.com/user_new/info/GetJDUserInfoUnion"
    method = 'GET'
    headers = {
        "Host": "me-api.jd.com",
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.42",
        "Accept-Language": "zh-cn",
        "Referer": "https://home.m.jd.com/myJd/newhome.action?sceneval=2&ufc=&",
        "Accept-Encoding": "gzip, deflate, br"
    }
    r =  requests.request(method, url, headers=headers)
    # 检测这里太快了, sleep一会儿, 避免FK
    await asyncio.sleep(random.uniform(0.5,2))

    try:
        if r.json().get('retcode') == str(1001):
            return True
    except:
        return True

    return False

async def main():
    ql = init_ql()
    cookies = await get_cookies(ql)

    disable_cookies_ids = {}

    for cookie in cookies:
        if await need_login(cookie['value']):
            disable_cookies_ids[cookie['id']] = cookie

    ql.disable_env(list(disable_cookies_ids.keys()))


    msg = "\n".join(
        [
            f"{cookie['remarks'].split('@')[0]} cookie 作废成功"
            for cookie in disable_cookies_ids.values()
        ]
    )
    send("京东cookie强制失效", msg)


if __name__ == "__main__":
    asyncio.run(main())
