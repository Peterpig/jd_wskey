"""
new Env('京东cookie自动复制');
cron: 1 10 * * * jd_cookie_copy.py
"""
import asyncio
import logging
import os

from qinglong import Qinglong, init_ql
from utils.utils import get_cookies

logger = logging.getLogger(__name__)

try:
    from notify import send
except:
    send = lambda *args: ...


async def main():
    ql = init_ql()
    cookies = await get_cookies(ql)

    host = '127.0.0.1:5700'
    client_id = '0eRdY1f-NmOH'
    client_secret = 'akP6_WpzMI35aOX6Njg-uqqJ'


    json_config = {"host": host, "client_id": client_id, "client_secret": client_secret}

    local_qinglong = Qinglong(json_config)
    local_cookies = await get_cookies(local_qinglong)
    local_cookies.delete_env([x['id'] for x in local_cookies])

    for ck in cookies:
        ck_env_dict = [{
            "value": ck,
            "name": "JD_COOKIE",
            "remarks": f"自动新增",
        }]
        local_cookies.insert_env(data=ck_env_dict)


    msg = "\n".join(
        [
            f"{cookie['remarks'].split('@')[0]} cookie 作废成功"
            for cookie in cookies
        ]
    )
    send("京东cookie强制失效", msg)



if __name__ == "__main__":
    asyncio.run(main())
