import base64
import json
import random
import re
import time
from io import BytesIO

import fire
import pyautogui
import requests
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from qinglong import init_ql
from utils.selenium_browser import get_browser
from utils.color_and_shape import get_text_by_tips, get_tips, get_X_Y
from utils.slide import slider_img, get_html_base_postion
from utils.utils import get_cookies, get_logger, try_many_times
from utils.bitwarden import get_username_passwd_from_bit

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

    targets = []
    target_num = 1

    if tip_type == 'sequential':
        target_num = 4
        res = get_text_by_tips(cpc_image_path, tip)
        print(f"res == {json.dumps(res, indent=2, ensure_ascii=False)}")
        if (not res) or (len(res) != target_num):
           return
        try:
            targets = [(postion['x'], postion['y']) for tip, postion in res]
        except Exception as e:
            return False
    else:
        res = get_X_Y(cpc_image_path, tip)
        X, Y = res['X'], res['Y']
        targets.append((X, Y))

    # chrome窗口坐标 + 图片坐标 + 鼠标偏移
    base_x, base_y = get_html_base_postion(browser)
    rect_x, rect_y = int(cpc_img.rect['x']), int(cpc_img.rect['y'])

    if not targets:
        logger.error(f"未获到坐标")
        return False

    for target in targets:
        X_abs = base_x + rect_x + target[0]
        Y_abs = base_y + rect_y + target[1]

        browser.switch_to.window(browser.current_window_handle)
        pyautogui.moveTo(X_abs, Y_abs)
        pyautogui.click()
        time.sleep(random.random())


    # 获取人工打得标记
    sign_span = []
    sleep_time = 10
    while sleep_time > 0:
        sign_span = getElement(browser, By.CLASS_NAME, "cs-sign-span", time=10, all=True)
        if sign_span and len(sign_span) == target_num:
            break
        time.sleep(1)
        sleep_time -= 1

    if len(sign_span) != target_num:
        return

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
            navimg = getElement(browser, By.CLASS_NAME, "nav-img", time=1)
            if navimg:
                with open(f"./images/{file_name}_info.json", "w+") as f:
                    f.write(json.dumps(img_info, indent=4, ensure_ascii=False))
                return True
        except:
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

    logger.info(f"设置cookie成功:{username}")
    return f'{username}'



async def main(*bit_users):
    qinglong = init_ql()
    envlist = await get_cookies(qinglong)

    # 如果没有传要登录的账户，自动从qinglong读取过期ck
    if not bit_users:
        disable_cookies = list(filter(lambda x: x["status"] != 0, envlist))
        if not disable_cookies:
            logger.info(f"暂未获取到过期cookie，全部更新！")
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
