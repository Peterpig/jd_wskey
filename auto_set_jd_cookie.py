import base64
import json
import logging
import random
import subprocess
import time

import fire
import numpy as np
import pyautogui
from pytweening import easeInBounce, getPointOnLine
from selenium.webdriver import ActionChains
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from qinglong import init_ql
from selenium_browser import get_browser
from utils import try_many_times

jd_username = ""
jd_passwd = ""
ENV_KEEP_KEYS = {"id", "value", "name", "remarks"}

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)
import ddddocr

det = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)

"""
bit_id_map.json
{
    "昵称": "bitwarden项目的id",
    "昵称2": "bitwarden项目的id",
}
"""

bit_id_map = json.load(open("./bit_id_map.json"))


def indify_img(background_b64, target_b64):
    background_bytes = base64.b64decode(
        background_b64.replace("data:image/jpg;base64,", "")
    )
    target_bytes = base64.b64decode(target_b64.replace("data:image/png;base64,", ""))
    res = det.slide_match(target_bytes, background_bytes, simple_target=True)
    return res["target"]


def getElement(driver, locateType, locatorExpression, time=10):
    try:
        element = WebDriverWait(driver, time).until(
            lambda x: x.find_element(by=locateType, value=locatorExpression)
        )
    except Exception as e:
        element = None
    return element


def send_keys_interval(element, text, interval=0.1):
    """
    webdriver 模拟人输入文本信息
    """
    for c in text:
        element.send_keys(c)
        time.sleep(random.randint(int(interval * 500), int(interval * 1500)) / 1000)


def slider_img(browser):
    if not getElement(browser, By.ID, "cpc_img"):
        return True

    # 安全验证
    background = browser.find_element(By.ID, "cpc_img")
    target = browser.find_element(By.ID, "small_img")
    silder_p = browser.find_element(By.CLASS_NAME, "sp_msg")
    silder = silder_p.find_element(By.TAG_NAME, "img")

    res = indify_img(
        background_b64=background.get_attribute("src"),
        target_b64=target.get_attribute("src"),
    )
    # 全屏
    # distance = res[0] * 421 / 275

    # 500x700分辨率
    offset = res[0] * 375 / 275
    position = browser.get_window_position()
    panel_height = browser.execute_script(
        "return window.outerHeight - window.innerHeight"
    )
    rect = silder.rect

    X, Y = (
        position["x"] + rect["x"] + (rect["width"] / 2),
        position["y"] + silder.location["y"] + panel_height + (rect["height"] / 2),
    )
    pyautogui.moveTo(X, Y)
    pyautogui.dragTo(
        X + offset, Y, random.randint(3, 5), pyautogui.easeInOutBack, button="left"
    )
    time.sleep(random.random())


def verify_code(browser):
    msgBtn = getElement(browser, By.CLASS_NAME, "getMsg-btn")
    if not (msgBtn and "获取验证码" in msgBtn.text):
        return

    msgBtn.click()
    slider_img(browser)

    logger.error("需要短信认证, 已经发送短信，请查收")
    msgCode = getElement(browser, By.CLASS_NAME, "msgCode")
    complete = False
    while not complete:
        code = msgCode.get_attribute("value")
        logger.error(f"验证码: {code}")
        if len(code) >= 6:
            browser.implicitly_wait(1000)
            btn = getElement(browser, By.CLASS_NAME, "btn")
            btn.click()

            browser.implicitly_wait(1000)
            btn = getElement(browser, By.CLASS_NAME, "btn")
            if btn:
                logger.error(f"验证码错误")
                time.sleep(60)
                btn.click()


def slider_verification(browser):
    time.sleep(random.random())
    if not getElement(browser, By.ID, "cpc_img"):
        return True

    # 安全验证
    slider_img(browser)
    voicemode = getElement(browser, By.CLASS_NAME, "voice-mode", 3)
    if voicemode:
        browser.implicitly_wait(1000)
        logger.error("需要短信认证")
        voicemode.click()
        verify_code(browser)

    if getElement(browser, By.CLASS_NAME, "sure_btn"):
        logger.error("滑块验证失败，请手动处理验证码")
        return False

    elif getElement(browser, By.ID, "cpc_img"):
        time.sleep(random.random())
        return slider_verification(browser)

    return True


@try_many_times(fail_exit=True)
def get_ck(jd_username, jd_passwd):
    browser = get_browser()
    # browser.maximize_window()
    wait = WebDriverWait(browser, timeout=20)

    for n in range(50):
        browser.get("https://plogin.m.jd.com/login/login")
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

        send_keys_interval(username, jd_username)
        send_keys_interval(password, jd_passwd)

        policy.click()
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "btn-active")))
        login.click()
        time.sleep(random.random())

        success = slider_verification(browser)
        if not success:
            continue

        # wait.until(EC.presence_of_element_located((By.ID, "msShortcutMenu")))
        # browser.get("https://home.m.jd.com/myJd/newhome.action")
        # username2 = getElement(browser, By.CLASS_NAME, "my_header_name").text

        pt_key, pt_pin, cookie = "", "", ""
        for _ in browser.get_cookies():
            if _["name"] == "pt_key":
                pt_key = _["value"]
            elif _["name"] == "pt_pin":
                pt_pin = _["value"]

        if pt_key and pt_pin:
            break

    cookie = {
        "pt_key": pt_key,
        "pt_pin": pt_pin,
        "__time": time.time(),
    }
    print(f"获取到cookie是：{cookie}")
    browser.quit()
    return cookie


def serch_ck(pin, envlist):
    for env in envlist:
        if pin in env["value"]:
            return env


@try_many_times(fail_exit=True)
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

    logger.info(f"设置cookie成功， ")


def get_username_passwd_from_bit(bit_id):
    try:
        out_bytes = subprocess.check_output(
            ["/usr/local/bin/bw", "get", "item", bit_id]
        )
    except subprocess.CalledProcessError as e:
        logger.error("获取bit信息失败1！！")
        raise e

    try:
        info = json.loads(out_bytes.decode())
        login = info["login"]
        return login["username"], login["password"]
    except (KeyError, ValueError) as e:
        logger.error("解析bit信息失败2！！, ", out_bytes)
        raise e


def main(*bit_users):
    qinglong = init_ql()
    envlist = qinglong.get_env()
    envlist = list(filter(lambda x: "name" in x and x["name"] == "JD_COOKIE", envlist))

    # bit_users = ["楠楠"]
    for bit_username in bit_users:
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
