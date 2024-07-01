import base64
import datetime
import json
import logging
import math
import random
import re
import subprocess
import sys
import time
from datetime import timedelta, timezone
from io import BytesIO

import fire
import pyautogui
import requests
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from color_and_shape import get_X_Y
from qinglong import init_ql
from selenium_browser import get_browser
from slide import slide_match
from utils import get_cookies, get_logger, try_many_times

jd_username = ""
jd_passwd = ""
ENV_KEEP_KEYS = {"id", "value", "name", "remarks"}

#logging.basicConfig(level=logging.INFO, format="%(message)s")
#logger = logging.getLogger(__name__)
logger = get_logger(__file__.replace('.py', ''))


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
    res = slide_match(target_bytes, background_bytes, simple_target=True)
    return res["target"]


def getElement(driver, locateType, locatorExpression, time=5):
    try:
        # element = WebDriverWait(driver, time).until(
        #     lambda x: x.find_element(by=locateType, value=locatorExpression)
        # )
        element = WebDriverWait(driver, time).until(
            EC.presence_of_element_located((locateType, locatorExpression))
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

# 获取html元素左上角坐标
def get_html_base_postion(browser):
    position = browser.get_window_position()
    panel_height = browser.execute_script(
        "return window.outerHeight - window.innerHeight"
    )

    return position['x'], position['y'] + panel_height

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

    # cpc_img 图片属性如下
    # Rendered size 展示的大小:	290 × 179 px
    # Intrinsic size 原始大小:	275 × 170 px
    # offset = res[0] * Rendered[0] / Intrinsic[0]
    Rendered = background.get_attribute("offsetWidth")
    Intrinsic = background.get_attribute("naturalWidth")


    offset = res[0] * float(Rendered) / float(Intrinsic)

    base_x, base_y = get_html_base_postion(browser)
    rect = silder.rect

    X, Y = (
        base_x + rect["x"] + (rect["width"] / 2),
        base_y + silder.location["y"] + (rect["height"] / 2),
    )

    x_ori, y_ori = pyautogui.position()
    logger.info(f"移动至 {x_ori, y_ori}")

    random_offset = random.randint(0, 3) * random.choice([-1, 1])

    pyautogui.moveTo(X, Y)
    pyautogui.dragTo(
        X + offset, Y, random.randint(2, 3), pyautogui.easeInOutBack, button="left"
    )
    time.sleep(random.random())

    pyautogui.moveTo(x_ori, y_ori)


def verify_code(browser):
    msgBtn = getElement(browser, By.CLASS_NAME, "getMsg-btn")
    if not (msgBtn and "获取验证码" in msgBtn.text):
        return

    msgBtn.click()
    slider_img(browser)

    logger.error("需要短信认证, 已经发送短信，请查收")
    msgCode = getElement(browser, By.CLASS_NAME, "msgCode")
    msgCode.click()
    complete = False
    while not complete:
        code = msgCode.get_attribute("value")
        logger.error(f"验证码: {code}")
        if len(code) >= 6:
            btn = getElement(browser, By.CLASS_NAME, "btn")
            btn.click()
            complete = True
            logger.error(f"验证码验证成功！！")
            break
        time.sleep(1)

def save_image(src, file_name):

    if isinstance(src, bytes):
        with open(f"./images/{file_name}.png", "wb") as f:
            f.write(src)
        return f"./images/{file_name}.png"
    else:
        img_head, img_type, img_body = re.search("^(data:image\/(.+);base64),(.+)$", src).groups()
        img = Image.open(BytesIO(base64.b64decode(img_body)))
        img.save(f"./images/{file_name}.{img_type}")
        return f"./images/{file_name}.{img_type}"


def cpc_img_info(browser):
     # 保存图片
    file_name = time.strftime("%Y%m%d%H%M%S", time.localtime())
    try:
        tip = browser.find_element(By.CLASS_NAME, "captcha_footer").find_element(By.TAG_NAME, "img")
        cpc_img = browser.find_element(By.ID, "cpc_img")
        tip_screenshot_as_png = tip.screenshot_as_png

        tip_src = tip.get_attribute("src")
        img = cpc_img.get_attribute("src")

        # 根据时间生成文件名
        cpc_image_path = save_image(img, f"{file_name}_cpc")
        save_image(tip_src, f"{file_name}_tip")
        tip_image_path = save_image(tip_screenshot_as_png, f"{file_name}_tip_screenshot")
    except Exception as e:
        print(e)
        return False

    img_info = {
        "cpc": {
            "rect": cpc_img.rect
        },
        "tip": {
            "rect": tip.rect
        },
        "sign_span": {
            "rect":    {},
            "position": {}
        }
    }


    try:
        # 计算坐标
        res = get_X_Y(cpc_image_path, tip_image_path)
        X, Y = res['X'], res['Y']

        if not (X and Y):
            logger.error(f"未获到坐标：{json.dumps(res['cnts_list'], indent=4, ensure_ascii=False)}")
            return False

        logger.info(f"计算到坐标 {X, Y}")

        # chrome窗口坐标 + 图片坐标 + 鼠标偏移
        base_x, base_y = get_html_base_postion(browser)

        X_abs = base_x + int(cpc_img.rect['x']) + X
        Y_abs = base_y + int(cpc_img.rect['y']) + Y

        logger.info(f"获取到坐标 {X_abs, Y_abs} 移动鼠标 ！")
        pyautogui.moveTo(X_abs, Y_abs)
        time.sleep(random.random())
        pyautogui.click()
    except Exception as e:
        logger.error(e)
        return False

    # 获取人工打得标记
    sign_span = getElement(browser, By.CLASS_NAME, "cs-sign-span", time=10)
    if sign_span:
        cpc_img = browser.find_element(By.ID, "cpc_img")
        img_info["sign_span"]["rect"] = sign_span.rect
        img_info["sign_span"]["position"] = {
            "top": sign_span.value_of_css_property("top"),
            "left": sign_span.value_of_css_property("left")
        }

        save_image(cpc_img.screenshot_as_png, f"{file_name}_cpc_screenshot")
        sure_btn = browser.find_element(By.CLASS_NAME, "captcha_footer").find_element(By.TAG_NAME, "button")

        if sure_btn:
            logger.info("获取sign_span mark成功！登录中....")
            sure_btn.click()

            # 只要成功的数据
            navimg = getElement(browser, By.CLASS_NAME, "nav-img")
            if navimg:
                with open(f"./images/{file_name}_info.json", "w+") as f:
                    f.write(json.dumps(img_info, indent=4, ensure_ascii=False))
                return True

    return False


def slider_verification(browser):
    time.sleep(random.random())
    if not getElement(browser, By.ID, "cpc_img"):
        return True

    # 安全验证
    slider_img(browser)
    voicemode = getElement(browser, By.CLASS_NAME, "voice-mode")
    if voicemode:
        logger.error("需要短信认证")
        voicemode.click()
        verify_code(browser)

    logger.info("判断中....")
    if getElement(browser, By.CLASS_NAME, "tip"):
        logger.error("滑块验证失败，请手动处理图形验证码!")
        cpc_img_info(browser)

    elif getElement(browser, By.ID, "cpc_img"):
        logger.error("滑块验证失败，再次重试!")
        time.sleep(random.random() * 10)
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

        # wait.until(EC.presence_of_element_located((By.ID, "username")))
        # wait.until(EC.presence_of_element_located((By.ID, "pwd")))
        # wait.until(EC.presence_of_element_located((By.CLASS_NAME, "planBLogin")))
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

        pt_key, pt_pin, cookie = "", "", ""
        for _ in browser.get_cookies():
            if _["name"] == "pt_key":
                pt_key = _["value"]
            elif _["name"] == "pt_pin":
                pt_pin = _["value"]

            if pt_key and pt_pin:
                break

        if pt_key and pt_pin:
            break

    cookie = {
        "pt_key": pt_key,
        "pt_pin": pt_pin,
        "__time": time.time(),
    }
    logger.info(f"获取到cookie是：{cookie}")
    browser.quit()
    return cookie

async def main_local(*bit_users):
    users = json.load(open('jd_pass.json'))
    while True:
        user = random.choice(users)
        print(user)
        get_ck(*user)

if __name__ == "__main__":
    fire.Fire(main_local)
