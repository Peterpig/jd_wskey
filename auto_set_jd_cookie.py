import base64
import datetime
import json
import random
import re
import subprocess
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

from qinglong import init_ql
from selenium_browser import get_browser
from utils.chaojiying import chaojiying_client
from utils.color_and_shape import get_text_by_tips, get_tips, get_X_Y
from utils.slide import slide_match
from utils.utils import get_cookies, get_logger, try_many_times

ENV_KEEP_KEYS = {"id", "value", "name", "remarks"}

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


def getElement(driver, locateType, locatorExpression, time=5, all=False):
    try:
        if all:
            element = WebDriverWait(driver, time).until(
                EC.presence_of_all_elements_located((locateType, locatorExpression))
            )
        else:
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
    browser.switch_to.window(browser.current_window_handle)

    pyautogui.moveTo(X, Y)
    pyautogui.dragTo(
        X + offset, Y, random.randint(2, 3), pyautogui.easeInOutBack, button="left"
    )
    pyautogui.moveTo(x_ori, y_ori)
    return True


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
        "sign_span": [
            # {
            #     "rect":    {},
            #     "position": {}
            # }
        ]
    }


    tip, tip_type = get_tips(tip_image_path)
    logger.info(f"获取到tip: {tip}, type: {tip_type}")
    if not tip:
        return

    # targets = []
    # pic_id = None
    # if tip_type == 'sequential':
    #     res, pic_id = get_text_by_tips(cpc_image_path, tip)
    #     if not res:
    #         return
    #     try:
    #         targets = [(postion['x'], postion['y']) for tip, postion in res.items()]
    #     except Exception as e:
    #         return False
    # else:
    #     res = get_X_Y(cpc_image_path, tip)
    #     X, Y = res['X'], res['Y']
    #     targets.append((X, Y))

    # # chrome窗口坐标 + 图片坐标 + 鼠标偏移
    # base_x, base_y = get_html_base_postion(browser)
    # rect_x, rect_y = int(cpc_img.rect['x']), int(cpc_img.rect['y'])

    # if not targets:
    #     logger.error(f"未获到坐标")
    #     return False

    # for target in targets:
    #     X_abs = base_x + rect_x + target[0]
    #     Y_abs = base_y + rect_y + target[1]

    #     browser.switch_to.window(browser.current_window_handle)
    #     pyautogui.moveTo(X_abs, Y_abs)
    #     pyautogui.click()
    #     time.sleep(random.random())

    # try:

    #     # 计算坐标
    #     res = get_X_Y(cpc_image_path, tip_image_path)
    #     X, Y = res['X'], res['Y']

    #     if not (X and Y):
    #         logger.error(f"未获到坐标：{res}")
    #         return False

    #     logger.info(f"计算到坐标 {X, Y}")

    #     # chrome窗口坐标 + 图片坐标 + 鼠标偏移
    #     base_x, base_y = get_html_base_postion(browser)

    #     X_abs = base_x + int(cpc_img.rect['x']) + X
    #     Y_abs = base_y + int(cpc_img.rect['y']) + Y

    #     logger.info(f"获取到坐标 {X_abs, Y_abs} 移动鼠标 ！")
    #     browser.switch_to.window(browser.current_window_handle)
    #     pyautogui.moveTo(X_abs, Y_abs)
    #     pyautogui.click()
    #     time.sleep(random.random())
    # except Exception as e:
    #     logger.error(e)
    #     return False


    # 获取人工打得标记
    sign_span = getElement(browser, By.CLASS_NAME, "cs-sign-span", time=10, all=True)
    if sign_span:
        cpc_img = browser.find_element(By.ID, "cpc_img")
        for sign in sign_span:
            img_info["sign_span"].append(
                {
                    "rect": sign.rect,
                    "position": {
                        "top": sign.value_of_css_property("top"),
                        "left": sign.value_of_css_property("left")
                    }
                }
            )

        save_image(cpc_img.screenshot_as_png, f"{file_name}_cpc_screenshot")
        sure_btn = browser.find_element(By.CLASS_NAME, "captcha_footer").find_element(By.TAG_NAME, "button")

        if sure_btn:
            logger.info("获取sign_span mark成功！登录中....")
            sure_btn.click()

            # 只要成功的数据
            try:
                navimg = getElement(browser, By.CLASS_NAME, "nav-img")
                if navimg:
                    with open(f"./images/{file_name}_info.json", "w+") as f:
                        f.write(json.dumps(img_info, indent=4, ensure_ascii=False))
                    return True
                elif pic_id:
                    chaojiying_client.ReportError(pic_id)
                    return False
            except:
                if pic_id:
                    chaojiying_client.ReportError(pic_id)
                return False

    return False


def verification(browser):
    time.sleep(random.random())

    if not getElement(browser, By.ID, "cpc_img"):
        return True

    voicemode = getElement(browser, By.CLASS_NAME, "voice-mode", 1)
    if voicemode:
        logger.error("需要短信认证")
        voicemode.click()
        verify_code(browser)

    while True:
        textTip = getElement(browser, By.CLASS_NAME, "text-tip")

        logger.info("开始处理验证....")
        if textTip and "拖动箭头" in textTip.text:
            logger.info("开始滑块验证....")
            slider_img(browser)


        if getElement(browser, By.CLASS_NAME, "tip"):
            logger.error("滑块验证失败，开始图形识别....")
            cpc_img_info(browser)

        navimg = getElement(browser, By.CLASS_NAME, "nav-img")
        if navimg:
            return True

        logger.info(f"验证失败，刷新一下")
        jcap_refresh = getElement(browser, By.CLASS_NAME, "jcap_refresh")
        jcap_refresh.click()
        time.sleep(random.random())


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

        success = verification(browser)
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


def serch_ck(pin, envlist):
    for env in envlist:
        if pin in env["value"]:
            return env


@try_many_times(fail_exit=True)
def set_qinglong_ck(qinglong, envlist, cookie, username):
    ck = (
        f"pt_key={cookie['pt_key']};pt_pin={cookie['pt_pin']};__time={cookie['__time']};username={username};"
    )

    ck_env_dict = serch_ck(cookie["pt_pin"], envlist)
    if not ck_env_dict:
        # fmt: off
        ck_env_dict = [{
            "value": ck,
            "name": "JD_COOKIE",
            "remarks": f"{username}(自动新增)",
        }]
        # fmt: one

        qinglong.insert_env(data=ck_env_dict)
        logger.info(f'{ username } 新增cookie成功！')
        return

    ck_env_dict["value"] = ck
    ck_env_dict = {k: v for k, v in ck_env_dict.items() if k in ENV_KEEP_KEYS}
    qinglong.set_env(data=ck_env_dict)

    envlist = list(filter(lambda x: "name" in x and x["name"] == "JD_COOKIE", envlist))
    qinglong.set_env(data=ck_env_dict)

    logger.info(f"设置cookie成功:{username}")
    return f'{username}'


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


async def main(*bit_users):
    qinglong = init_ql()
    envlist = await get_cookies(qinglong)
    beijing = timezone(timedelta(hours=8))
    now = datetime.datetime.now(beijing)
    force_refesh_start = now.replace(hour=1, minute=30, second=0)
    force_refesh_end = now.replace(hour=2, minute=0, second=0)
    force_refesh = True

    # 如果没有传要登录的账户，自动从qinglong读取过期ck
    if not bit_users:
        disable_cookies = list(filter(lambda x: x["status"] != 0, envlist))
        if not disable_cookies:
            logger.info(f"暂未获取到过期cookie!")
            if force_refesh_start < now < force_refesh_end or force_refesh:
                bit_users = bit_id_map.keys()

        else:
            bit_users = list(map(lambda x: x['remarks'].split('@')[0], disable_cookies))


    if not bit_users:
        logger.info(f"暂未获取到过期账户!")
        return

    msgs = []
    logger.info(f"自动设置账户：{bit_users}")
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

        msg = set_qinglong_ck(qinglong, envlist, cookie, bit_username)
        if msg:
            msgs.append(msg)

    if msgs:
        msg_str = '\n'.join(msgs)
        msg_str += '\nCookie设置成功!'
        requests.get(f'https://bark.6tun.com/dvvFu9p3TvZHrHipusfUKi/京东Cookie设置成功/{msg_str}')

if __name__ == "__main__":
    fire.Fire(main)
