'''
new Env('京东wskey自动转换');
cron: 30 8 * * * wskey.py
'''
import base64
import json
import logging
import os
import re
import sys
import time
import urllib

import requests
import urllib3
from fake_useragent import UserAgent

from qinglong import Qinglong

urllib3.disable_warnings()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

WSKEY_P = re.compile(f"pin=([^;\s]+);wskey=([^;\s]+);")
CK_P = re.compile(r"pt_key=([^;\s]+);pt_pin=([^;\s]+);")
ENV_KEEP_KEYS = {"id", "value", "name", "remarks"}

try:
    from notify import send  # 导入青龙消息通知模块
except:
    send = None



def get_wskey():
    if "JD_WSCK" not in os.environ:
        logger.info("未添加JD_WSCK变量")
        sys.exit(0)

    wskey_list = os.environ["JD_WSCK"].split("&")

    # fmt: off
    wskey_list = (
        filter(lambda x: x,
            map(lambda x: WSKEY_P.match(x), wskey_list)
        )
        or []
    )
    # fmt: on

    if not wskey_list:
        logger.info("未添加JD_WSCK变量")
        sys.exit(0)

    return wskey_list


def gen_params():
    url_list = ["aHR0cHM6Ly9hcGkubW9tb2UubWwv", "aHR0cHM6Ly9hcGkuaWxpeWEuY2Yv"]
    for i in url_list:
        url = str(base64.b64decode(i).decode())
        url_token = url + "api/genToken"
        url_check = url + "api/check_api"

        headers = {"authorization": "Bearer Shizuku"}
        res = requests.get(
            url=url_check, verify=False, headers=headers, timeout=20
        ).text
        c_info = json.loads(res)
        ua = c_info["User-Agent"]
        headers = {"User-Agent": ua}
        params = requests.get(
            url=url_token, headers=headers, verify=False, timeout=20
        ).json()

        return params


def gen_jd_cookie(wskey, params):
    ua = UserAgent().google
    headers = {
        "cookie": wskey,
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "charset": "UTF-8",
        "accept-encoding": "br,gzip,deflate",
        "user-agent": ua,
    }

    url = "https://api.m.jd.com/client.action"  # 设置 URL地址
    data = "body=%7B%22to%22%3A%22https%253a%252f%252fplogin.m.jd.com%252fjd-mlogin%252fstatic%252fhtml%252fappjmp_blank.html%22%7D&"

    res = requests.post(
        url=url, params=params, headers=headers, data=data, verify=False, timeout=10
    )
    res_json = json.loads(res.text)
    tokenKey = res_json["tokenKey"]

    headers = {
        "User-Agent": ua,
        "accept": "accept:text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "x-requested-with": "com.jingdong.app.mall",
    }
    params = {
        "tokenKey": tokenKey,
        "to": "https://plogin.m.jd.com/jd-mlogin/static/html/appjmp_blank.html",
    }

    url = "https://un.m.jd.com/cgi-bin/app/appjmp"
    res = requests.get(
        url=url,
        headers=headers,
        params=params,
        verify=False,
        allow_redirects=False,
        timeout=20,
    )

    res_set = res.cookies.get_dict()
    pt_key = "pt_key=" + res_set["pt_key"]
    pt_pin = "pt_pin=" + res_set["pt_pin"]

    ck = f"{pt_key};{pt_pin};__time={time.time()}"
    return ck


def check_ck_is_ok(ckenv):
    # ckenv = {
    #     "id": 1,
    #     "value": "pt_key=xx;pt_pin=xxx;",
    #     "name": "JD_COOKIE",
    #     "remarks": "xx",
    # }
    ck = ckenv["value"]
    ck_math = CK_P.match(ck)
    pin = ck_math.group(2)

    url = "https://me-api.jd.com/user_new/info/GetJDUserInfoUnion"  # 设置JD_API接口地址
    headers = {
        "Cookie": ck,
        "Referer": "https://home.m.jd.com/myJd/home.action",
        "user-agent": UserAgent().google,
    }
    try:
        # reuest = retry_request()
        res = requests.get(
            url=url, headers=headers, verify=False, timeout=10, allow_redirects=False
        )
    except Exception as err:
        logger.info("JD接口错误 请重试或者更换IP")
        return False

    if res.status_code != 200:
        logger.info("JD接口错误码: " + str(res.status_code))
        return False

    code = int(json.loads(res.text)["retcode"])
    if code != 0:
        return False

    return True


def serch_ck(pin, envlist):
    for env in envlist:
        if pin in env["value"]:
            return env

def main():
    host = os.environ.get('host')
    client_id = os.environ.get('client_id')
    client_sercet = os.environ.get('client_sercet')

    if not (host and client_id and client_sercet):
        logger.error("请设置青龙环境环境变量 host、client_id、client_sercet!")
        sys.exit(0)

    json_config = {
        "host": host,
        "client_id": client_id,
        "client_sercet": client_sercet
    }
    qinglong = Qinglong(json_config)
    envlist = qinglong.get_env()
    envlist = filter(lambda x: "name" in x and x["name"] == "JD_COOKIE", envlist)
    wskey_list = get_wskey()
    params = gen_params()

    for wskey_match in wskey_list:
        wskey = wskey_match.string
        ws_pin = wskey_match.group(1)
        ws_pin_name = urllib.parse.unquote(ws_pin)
        ws_key = wskey_match.group(2)

        ck_env_dict = serch_ck(ws_pin, envlist)
        # cookie不存在
        if not ck_env_dict:
            ck = gen_jd_cookie(wskey, params)
            # fmt: off
            ck_env_dict = [{
                "value": ck,
                "name": "JD_COOKIE",
                "remakrs": "wskey自动生成"
            }]
            # fmt: one
            qinglong.insert_env(data=ck_env_dict)
            logger.info(f'账户 {ws_pin_name} 新增cookie成功！')
            continue

        logger.info(f'开始检测账户 {ws_pin_name} cookie是否有效')
        if check_ck_is_ok(ck_env_dict):
            logger.info(f'账户 {ws_pin_name} cookie有效，暂不转换！')
            continue

        logger.info(f'账户 {ws_pin_name} cookie失效，开始使用wskey转换cookie！')
        ck = gen_jd_cookie(wskey, params)
        ck_env_dict["value"] = ck
        ck_env_dict = {k: v for k, v in ck_env_dict.items() if k in ENV_KEEP_KEYS}
        qinglong.set_env(data=ck_env_dict)
        logger.info(f'账户 {ws_pin_name} cookie转换成功！')


if __name__ == "__main__":
    main()
