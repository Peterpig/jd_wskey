import json
import logging
import os
import subprocess
import sys
import time

import fire
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from qinglong import init_ql
from selenium_browser import get_browser

jd_username = ""
jd_passwd = ""
ENV_KEEP_KEYS = {"id", "value", "name", "remarks"}

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


"""
bit_id_map.json
{
    "昵称": "bitwarden项目的id",
    "昵称2": "bitwarden项目的id",
}
"""

bit_id_map = json.load(open("./bit_id_map.json"))


def get_ck(jd_username, jd_passwd):
    browser = get_browser()
    browser.get("https://plogin.m.jd.com/login/login")

    wait = WebDriverWait(browser, 135)
    logger.info("请在网页端通过手机号码登录")

    wait.until(EC.presence_of_element_located((By.ID, "username")))
    wait.until(EC.presence_of_element_located((By.ID, "pwd")))
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "planBLogin")))
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "a")))

    planBLogin = browser.find_element(By.CLASS_NAME, "planBLogin")
    planBLogin.click()

    username = browser.find_element(By.ID, "username")
    password = browser.find_element(By.ID, "pwd")
    policy = browser.find_element(By.CLASS_NAME, "policy_tip-checkbox")
    login = browser.find_element(By.TAG_NAME, "a")

    username.send_keys(jd_username)
    password.send_keys(jd_passwd)

    policy.click()
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "btn-active")))

    login.click()
    wait.until(EC.presence_of_element_located((By.ID, "msShortcutMenu")))

    browser.get("https://home.m.jd.com/myJd/newhome.action")

    username2 = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "my_header_name"))
    ).text

    pt_key, pt_pin, cookie = "", "", ""
    for _ in browser.get_cookies():
        if _["name"] == "pt_key":
            pt_key = _["value"]
        if _["name"] == "pt_pin":
            pt_pin = _["value"]
        if pt_key and pt_pin:
            break

    cookie = {
        "username": username2,
        "pt_key": pt_key,
        "pt_pin": pt_pin,
        "__time": time.time(),
    }
    print(f"{username2} 获取到cookie是：{cookie}")
    return cookie


def serch_ck(pin, envlist):
    for env in envlist:
        if pin in env["value"]:
            return env


def set_qinglong_ck(qinglong, envlist, cookie):
    ck = (
        f"pt_key={cookie['pt_key']};pt_pin={cookie['pt_pin']};__time={cookie['__time']}"
    )

    ck_env_dict = serch_ck(cookie["pt_pin"], envlist)
    if not ck_env_dict:
        # fmt: off
        ck_env_dict = [{
            "value": ck,
            "name": "JD_COOKIE",
            "remarks": f"{cookie['username']}(自动新增)",
        }]
        # fmt: one

        qinglong.insert_env(data=ck_env_dict)
        logger.info(f'{ cookie["username"] } 新增cookie成功！')
        return

    ck_env_dict["value"] = ck
    ck_env_dict = {k: v for k, v in ck_env_dict.items() if k in ENV_KEEP_KEYS}
    qinglong.set_env(data=ck_env_dict)

    envlist = list(filter(lambda x: "name" in x and x["name"] == "JD_COOKIE", envlist))
    qinglong.set_env(data=ck_env_dict)

    logger.info(f"设置{cookie['username']} cookie成功， ")


def get_username_passwd_from_bit(bit_id):
    try:
        out_bytes = subprocess.check_output(["bw", "get", "item", bit_id])
    except subprocess.CalledProcessError as e:
        logger.error("获取bit信息失败！！")
        raise e

    try:
        info = json.loads(out_bytes.decode())
        login = info["login"]
        return login["username"], login["password"]
    except (KeyError, ValueError):
        logger.error("解析bit信息失败！！")
        raise e


def main(bit_uesrs: tuple):
    qinglong = init_ql()
    envlist = qinglong.get_env()
    envlist = list(filter(lambda x: "name" in x and x["name"] == "JD_COOKIE", envlist))

    for bit_username in bit_uesrs:
        bit_id = bit_id_map.get(bit_username)
        if not bit_id:
            logger.error(f"没找到{bit_username}对应的bit_id")
            continue

        try:
            jd_username, jd_passwd = get_username_passwd_from_bit(bit_id)
        except Exception as e:
            logger.error(e)
            continue

        logger.info(f"获取{bit_username}京东用户名密码成功， 开始获取cookie")
        cookie = get_ck(jd_username, jd_passwd)

        set_qinglong_ck(qinglong, envlist, cookie)


if __name__ == "__main__":
    fire.Fire(main)
