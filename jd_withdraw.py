"""
new Env('大赢家提现');
cron 58 59 23 * * *	jd_withdraw.py now
"""
import asyncio
import datetime
import os
import time
import uuid

import aiohttp

try:
    from notify import send  # 导入青龙消息通知模块
except:
    send = None

from itertools import product

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
    "d158ed723d411967d15471edf90a25ab",
    "d29967608439624bd4688e06254b6374",
    "c14b645cabaa332a883cc5f43a9dd2b7",
    "006d8d0f371e247333a302627af7da00",
    "018300fea81b5bf3f1cad271f7bcfda7",
]

withdraw_ids = [
    # {"id": "02b48428177a44a4110034497668f808", "name": "100元现金"},
    {"id": "7ea791839f7fe3168150396e51e30917", "name": "20元现金"},
    {"id": "da3fc8218d2d1386d3b25242e563acb8", "name": "8元现金"},
    {"id": "53515f286c491d66de3e01f64e3810b2", "name": "现金奖励3元"},
    {"id": "dac84c6bf0ed0ea9da2eca4694948440", "name": "1元现金"},
    {"id": "1848d61655f979f8eac0dd36235586ba", "name": "0.3元现金"},
    # {"id": "018300fea81b5bf3f1cad271f7bcfda7", "name": "20元红包"},
    # {"id": "006d8d0f371e247333a302627af7da00", "name": "5元红包"},
    # {"id": "c14b645cabaa332a883cc5f43a9dd2b7", "name": "3元红包"},
    # {
    #     "id": "d158ed723d411967d15471edf90a25ab",
    #     "name": "0.5红包"
    # },
    # {
    #     "id": "d29967608439624bd4688e06254b6374",
    #     "name": "1元红包"
    # }
]


async def request(remarks, session, url, name):
    for i in range(5):
        try:
            async with session.get(url) as r:
                json_body = await r.json()
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %f")

                if json_body["ret"] in [
                    248,
                ]:
                    raise Exception(f"{now} {remarks}: {name} {json_body['msg']}")

                return f"{now} {remarks}: {name} {json_body['msg']}"
        except Exception:
            await asyncio.sleep(0.01)


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


async def withdraw_one(cookie_dict, withdraw_row):
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

    async with aiohttp.ClientSession(headers=headers) as session:
        id, name = withdraw_row["id"], withdraw_row["name"]
        url = f"https://api.m.jd.com/api?functionId=jxPrmtExchange_exchange&appid=cs_h5&body=%7B%22bizCode%22%3A%22makemoneyshop%22%2C%22ruleId%22%3A%22{id}%22%2C%22sceneval%22%3A2%2C%22buid%22%3A325%2C%22appCode%22%3A%22%22%2C%22time%22%3A{time.time()}%2C%22signStr%22%3A%22%22%7D"
        return await request(remarks, session, url, name)


async def main():
    task_list = []
    await getToken()
    cookies = await getCookies()

    for row in product(cookies, withdraw_ids):
        cookie_dict, withdraw_row = row
        task = asyncio.create_task(withdraw_one(cookie_dict, withdraw_row))
        task_list.append(task)

    done, pending = await asyncio.wait(task_list, timeout=None)
    # 得到执行结果
    send_msg = []
    for done_task in done:
        res = done_task.result()
        if res and res != "None":
            print(f"{res}")
            send_msg.append(res)

    if send and send_msg:
        # send("提现成功", "\n".join(send_msg))
        pass


if __name__ == "__main__":
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    asyncio.run(main())
