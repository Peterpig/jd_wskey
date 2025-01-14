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

    host = 'http://127.0.0.1:5700'
    client_id = os.environ.get("local_client_id")
    client_secret = os.environ.get("local_client_secret")

    json_config = {"host": host, "client_id": client_id, "client_secret": client_secret}

    local_qinglong = Qinglong(json_config)
    local_cookies = await get_cookies(local_qinglong)
    if local_cookies:
        local_qinglong.delete_env([x['id'] for x in local_cookies])

    for ck in cookies:
        ck_env_dict = [{
            "value": ck['value'],
            "name": "JD_COOKIE",
            "remarks": f"{ck['remarks']}自动新增",
        }]
        local_qinglong.insert_env(data=ck_env_dict)


    msg = "\n".join(
        [
            f"{cookie['remarks'].split('@')[0]} cookie 新增成功"
            for cookie in cookies
        ]
    )
    send("京东cookie-Copy成功", msg)



if __name__ == "__main__":
    asyncio.run(main())
