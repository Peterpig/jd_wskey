"""
new Env('大赢家提现');
cron 58 59 23 * * *	jd_withdraw.py now
"""
import asyncio
import os
import time
import datetime
import uuid

import aiohttp

ql = {
    "host": os.environ.get("host"),
    "client_id": os.environ.get("client_id"),
    "client_secret": os.environ.get("client_secret"),
    "token": None,
}

withdraw_ids = [
    "1848d61655f979f8eac0dd36235586ba",
    "dac84c6bf0ed0ea9da2eca4694948440",
    "53515f286c491d66de3e01f64e3810b2",
    "da3fc8218d2d1386d3b25242e563acb8",
    "7ea791839f7fe3168150396e51e30917",
    "02b48428177a44a4110034497668f808",

    # 红包
    "d71b23a381ada0934039d890ad22ab8d",
    "66d9058514891de12e96588697cc3bb3",
    "b141ddd915d20f078d69f6910b02a60a",
    "8609ec76a8a70db9a5443376d34fa26a",
]


async def withdraw(cookie_dict):
    cookie = cookie_dict["value"]
    remarks = cookie_dict["remarks"].split("@@")[0]
    UUID = str(uuid.uuid4()).replace("-", "")
    ADID = str(uuid.uuid4())

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        "Cookie": cookie,
        "Referer": "https://wqs.jd.com/",
        "User-Agent": f"jdapp;iPhone;9.5.4;13.6;${UUID};network/wifi;ADID/${ADID};model/iPhone10,3;addressid/0;appBuild/167668;jdSupportDarkMode/0;Mozilla/5.0 (iPhone; CPU iPhone OS 13_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148;supportJDSHWK/1",
    }

    async def request(session, url):
        for i in range(5):
            try:
                async with session.get(url) as r:
                    json_body = await r.json()
                    now = datetime.datetime.now().strftime( '%Y-%m-%d %H:%M:%S %f')

                    if json_body['ret'] in [248, ]:
                        raise Exception(f"{now} {remarks}: {json_body['msg']}")

                    if json_body['ret'] in [0, ]:
                        return f"{now} {remarks}: {json_body['msg']}"

                    return f"{now} {remarks}: {json_body['msg']}"
            except Exception:
                await asyncio.sleep(0.01)

    async with aiohttp.ClientSession(headers=headers) as session:
        for id in withdraw_ids:
            url = f'https://api.m.jd.com/api?functionId=jxPrmtExchange_exchange&appid=cs_h5&body=%7B%22bizCode%22%3A%22makemoneyshop%22%2C%22ruleId%22%3A%22{id}%22%2C%22sceneval%22%3A2%2C%22buid%22%3A325%2C%22appCode%22%3A%22%22%2C%22time%22%3A{time.time()}%2C%22signStr%22%3A%22%22%7D'


            ret = await request(session, url)
            print(ret)
            # async with session.get(url) as r:
            #     try:
            #         json_body = await r.json()
            #         print(f"{remarks}: ", json_body)
            #     except Exception as e:
            #         await asyncio.sleep(0.1)
            #         r = await session.get(url)
            #         json_body = await r.json()
            #         print(f"{remarks}: ", json_body)
            #     # return json_body


async def getToken():
    if not ql["token"]:
        token_url = ql["host"] + "/open/auth/token"
        params = {"client_id": ql["client_id"], "client_secret": ql["client_secret"]}
        async with aiohttp.ClientSession() as session:
            async with session.get(token_url, params=params) as r:
                resp = await r.json()
                if resp and resp["data"] and resp["data"]["token"]:
                    ql["token"] = resp["data"]["token"]


async def getCookies():
    url = ql["host"] + "/open/envs"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36 Edg/94.0.992.38",
        "Authorization": f"Bearer {ql['token']}",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as r:
            resp = await r.json()
            return list(
                filter(lambda x: "name" in x and x["name"] == "JD_COOKIE", resp["data"])
            )


async def main():
    task_list = []
    await getToken()
    cookies = await getCookies()
    for cookie_dict in cookies[::-1]:
        task = asyncio.create_task(withdraw(cookie_dict))
        task_list.append(task)

    done, pending = await asyncio.wait(task_list, timeout=None)
    # 得到执行结果
    for done_task in done:
        print(f"{done_task.result()}")


if __name__ == "__main__":
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    asyncio.run(main())
