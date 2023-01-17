"""
new Env('大赢家提现');
cron: 58 23 * * * withdraw.py
"""

import asyncio
import os
import uuid

import aiohttp

ql = {
    "host": os.environ.get("host"),
    "client_id": os.environ.get("client_id"),
    "client_sercet": os.environ.get("client_sercet"),
    "token": None,
}


async def withdraw(id, cookie):
    UUID = str(uuid.uuid4()).replace("-", "")
    ADID = str(uuid.uuid4())

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        "Cookie": cookie,
        "Referer": "https://wqs.jd.com/",
        "User-Agent": f"jdapp;iPhone;9.5.4;13.6;$${UUID};network/wifi;ADID/$${ADID};model/iPhone10,3;addressid/0;appBuild/167668;jdSupportDarkMode/0;Mozilla/5.0 (iPhone; CPU iPhone OS 13_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148;supportJDSHWK/1",
    }

    url = (
        f"https://wq.jd.com/prmt_exchange/client/exchange?g_ty=h5&g_tk=&appCode=msc588d6d5&bizCode=makemoneyshop&ruleId=${id}&sceneval=2",
    )

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get("http://httpbin.org/headers") as r:
            json_body = await r.json()
            print("json_body === ", json_body)


async def getToken(host):
    if not ql["token"]:
        token_url = ql["host"] + "/open/envs"
        params = {"client_id": ql["client_id"], "client_secret": ql["client_secret"]}
        async with aiohttp.ClientSession() as session:
            async with session.get(token_url, params=params) as r:
                resp = await r.json()
                if resp and resp["token"]:
                    ql["token"] = resp["token"]


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
            envlist = await r.json()
            return list(
                filter(lambda x: "name" in x and x["name"] == "JD_COOKIE", envlist)
            )


async def main():
    await getToken()
    cookies = await getCookies()
    print(cookies)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
