"""
new Env('农场自动种植兑换');
cron 5 */2 * * * jd_farm_automation.py
"""

import asyncio
import datetime
import json
import logging
import os

import aiohttp
from dotmap import DotMap

from qinglong import init_ql

try:
    from notify import send
except:
    send = lambda *args: ...

logger = logging.getLogger(__name__)

ql = {
    "host": os.environ.get("host"),
    "client_id": os.environ.get("client_id"),
    "client_secret": os.environ.get("client_secret"),
    "token": None,
}

level = "2"

headers = {
    "Connection": "keep-alive",
    "Accept": "*/*",
    "Host": "api.m.jd.com",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.4(0x1800042c) NetType/4G Language/zh_CN miniProgram",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-cn",
}


async def get_cookies(qinglong):
    envs = qinglong.get_env()
    return list(filter(lambda x: "name" in x and x["name"] == "JD_COOKIE", envs))


async def api(cookie, fn, body):
    # url = f"""https://api.m.jd.com/client.action?functionId=${fn}&body=${json.dumps(body)}&client=apple&clientVersion=10.0.4&osVersion=13.7&appid=wh5&loginType=2&loginWQBiz=interact"""

    url = f"""https://api.m.jd.com/client.action?functionId={fn}&client=apple&clientVersion=10.0.4&osVersion=13.7&appid=wh5&loginType=2&loginWQBiz=interact"""

    headers["Cookie"] = cookie

    async with aiohttp.ClientSession(headers=headers) as session:
        for _ in range(5):
            try:
                async with session.get(url, params={"body": json.dumps(body)}) as r:
                    json_body = await r.json(content_type=None)
                    return DotMap(json_body)
            except Exception as e:
                logger.error(e)
                await asyncio.sleep(0.01)


def format_timestamp(t):
    dt = datetime.datetime.fromtimestamp(t / 1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


async def main_(cookie_dict):
    cookie = cookie_dict["value"]
    name = cookie_dict["remarks"].split("@@")[0]

    msg = f"【{name}】："
    info = await api(
        cookie, "initForFarm", {"version": 11, "channel": 3, "babelChannel": 0}
    )
    if info.code != "0":
        logger.info("可能没开通农场或者黑透了！！！")

    if info.farmUserPro.treeState == 1:
        return

    elif info.farmUserPro.treeState == 2:
        logger.info(
            f"{info.farmUserPro.name},种植时间：{format_timestamp(info.farmUserPro.createTime)}"
        )

        coupon = await api(
            cookie, "gotCouponForFarm", {"version": 11, "channel": 3, "babelChannel": 0}
        )
        logger.info(coupon)

        info = await api(
            cookie, "initForFarm", {"version": 11, "channel": 3, "babelChannel": 0}
        )

    elif info.farmUserPro.treeState == 3:
        hongBao = info.myHongBaoInfo.hongBao
        msg += f"已兑换{hongBao.discount}红包，{format_timestamp(hongBao.endTime)}过期"

    element = info.farmLevelWinGoods[level][0] or 0

    if not element:
        logger.info("'种子已抢完，下次在来!!!\n'")

    info = await api(
        cookie,
        "choiceGoodsForFarm",
        {
            "imageUrl": "",
            "nickName": "",
            "shareCode": "",
            "goodsType": element.type,
            "type": "0",
            "version": 11,
            "channel": 3,
            "babelChannel": 0,
        },
    )
    if info.code * 1 == 0:
        msg += f"\n再次种植【${info.farmUserPro.name}】"

    a = await api(
        cookie,
        "gotStageAwardForFarm",
        {"type": "4", "version": 11, "channel": 3, "babelChannel": 0},
    )
    b = await api(
        cookie,
        "waterGoodForFarm",
        {"type": "", "version": 11, "channel": 3, "babelChannel": 0},
    )
    c = await api(
        cookie,
        "gotStageAwardForFarm",
        {"type": "1", "version": 11, "channel": 3, "babelChannel": 0},
    )
    return msg


async def main():
    qinglong = init_ql()
    cookies = await get_cookies(qinglong)
    task_list = []
    for cookie_dict in cookies:
        task = asyncio.create_task(main_(cookie_dict))
        task_list.append(task)

    done, pending = await asyncio.wait(task_list, timeout=None)

    # 得到执行结果
    send_msg = []
    for done_task in done:
        res = done_task.result()
        if res and res != "None":
            print(f"{res}")
            send_msg.append(res)

    if send_msg:
        send("农场种植成功", "\n".join(send_msg))


if __name__ == "__main__":
    asyncio.run(main())
