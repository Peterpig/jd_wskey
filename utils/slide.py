import io
import pyautogui
import random
import time
import math

import base64
import cv2
import numpy as np
from PIL import Image
from selenium.webdriver.common.by import By

from utils.utils import get_logger

logger = get_logger(__file__.replace('.py', ''))


def get_target(img_bytes: bytes = None):
    image = Image.open(io.BytesIO(img_bytes))
    w, h = image.size
    starttx = 0
    startty = 0
    end_x = 0
    end_y = 0
    for x in range(w):
        for y in range(h):
            p = image.getpixel((x, y))
            if p[-1] == 0:
                if startty != 0 and end_y == 0:
                    end_y = y

                if starttx != 0 and end_x == 0:
                    end_x = x
            else:
                if startty == 0:
                    startty = y
                    end_y = 0
                else:
                    if y < startty:
                        startty = y
                        end_y = 0
        if starttx == 0 and startty != 0:
            starttx = x
        if end_y != 0:
            end_x = x
    return image.crop([starttx, startty, end_x, end_y]), starttx, startty

def slide_match(target_bytes: bytes = None, background_bytes: bytes = None, simple_target: bool=False, flag: bool=False):
    if not simple_target:
        try:
            target, target_x, target_y = get_target(target_bytes)
            target = cv2.cvtColor(np.asarray(target), cv2.IMREAD_ANYCOLOR)
        except SystemError as e:
            # SystemError: tile cannot extend outside image
            if flag:
                raise e
            return slide_match(target_bytes=target_bytes, background_bytes=background_bytes, simple_target=True, flag=True)
    else:
        target = cv2.imdecode(np.frombuffer(target_bytes, np.uint8), cv2.IMREAD_ANYCOLOR)
        target_y = 0
        target_x = 0

    background = cv2.imdecode(np.frombuffer(background_bytes, np.uint8), cv2.IMREAD_ANYCOLOR)

    background = cv2.Canny(background, 100, 200)
    target = cv2.Canny(target, 100, 200)

    background = cv2.cvtColor(background, cv2.COLOR_GRAY2RGB)
    target = cv2.cvtColor(target, cv2.COLOR_GRAY2RGB)

    res = cv2.matchTemplate(background, target, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    h, w = target.shape[:2]
    bottom_right = (max_loc[0] + w, max_loc[1] + h)
    return {"target_y": target_y,
            "target": [int(max_loc[0]), int(max_loc[1]), int(bottom_right[0]), int(bottom_right[1])]}


def indify_img(background_b64, target_b64):
    background_bytes = base64.b64decode(
        background_b64.replace("data:image/jpg;base64,", "")
    )
    target_bytes = base64.b64decode(target_b64.replace("data:image/png;base64,", ""))
    res = slide_match(target_bytes, background_bytes, simple_target=True)
    return res["target"]


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

    # 滑块开始位置
    X, Y = (
        base_x + rect["x"] + (rect["width"] / 2),
        base_y + silder.location["y"] + (rect["height"] / 2),
    )

    # 滑块结束位置
    X_TO, Y_TO = int(X + offset), int(Y + random.randint(2, 10))

    x_ori, y_ori = pyautogui.position()
    logger.info(f"从{X, Y}移动至 {X_TO, Y_TO}")
    browser.switch_to.window(browser.current_window_handle)

    # dragTo(X, Y, X_TO, Y_TO)
    human_like_drag(X, Y, X_TO, Y_TO)
    pyautogui.moveTo(x_ori, y_ori)
    return True


def dragTo(X, Y, X_TO, Y_TO):
    pyautogui.moveTo(X, Y)
    pyautogui.dragTo(
        X_TO,
        Y_TO,
        random.randint(2, 3),
        pyautogui.easeInOutBack, button="left"
    )


def human_like_drag(X, Y, X_TO, Y_TO):
    # 随机暂停时间，模拟人类的犹豫
    time.sleep(random.uniform(0.2, 0.5))  # 缩短暂停时间以加快整体操作

    # 移动到起始位置并按下鼠标
    pyautogui.moveTo(X, Y, random.uniform(0.1, 0.2), pyautogui.easeInOutQuad)
    pyautogui.mouseDown(button='left')

    # 模拟人类的犹豫
    time.sleep(random.uniform(0.1, 0.3))

    # 定义随机过冲和回拉
    overshoot_x = X_TO + random.uniform(10, 15)
    overshoot_y = Y_TO + random.uniform(10, 15)
    recovery_x = X_TO + random.uniform(-1, 2)
    recovery_y = Y_TO + random.uniform(-1, 2)

    # 使用曲线轨迹移动
    def move_with_curve(start_x, start_y, end_x, end_y, duration):
        mid_x = (start_x + end_x) / 2 + random.uniform(-10, 10)
        mid_y = (start_y + end_y) / 2 + random.uniform(-10, 10)

        pyautogui.moveTo(mid_x, mid_y, random.uniform(0.1, 0.3), pyautogui.easeInOutQuad)
        pyautogui.moveTo(end_x, end_y, duration, pyautogui.easeInOutQuad)

    # 执行曲线移动到目标的过冲点
    move_with_curve(X, Y, overshoot_x, overshoot_y, random.uniform(0.3, 0.5))

    # 随机暂停一小段时间，模拟人类调整
    time.sleep(random.uniform(0.1, 0.3))

    # 执行回拉操作
    move_with_curve(overshoot_x, overshoot_y, recovery_x, recovery_y, random.uniform(0.2, 0.3))

    # 松开鼠标
    pyautogui.mouseUp(button='left')