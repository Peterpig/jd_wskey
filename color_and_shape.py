import copy
import json
import platform
import re
from collections import OrderedDict

import cv2
import matplotlib.pyplot as plt
import numpy as np
from paddleocr import PaddleOCR
from PIL import ImageFont
from scipy.spatial import distance as dist

color_re = re.compile(r"请选出图中(.*?色)的图形")
shape_re = re.compile(r"请选出图中的(.*)")

def get_font():
    system = platform.system()

    if system == 'Darwin':  # macOS
        font_path = "/System/Library/Fonts/PingFang.ttc"
    elif system == 'Windows':
        font_path = "C:/Windows/Fonts/msyh.ttc"  # 使用微软雅黑作为替代字体
    elif system == 'Linux':
        font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
    else:
        raise RuntimeError(f"Unsupported OS: {system}")

    try:
        font = ImageFont.truetype(font_path, 4)
    except IOError:
        print(f"Font file not found at {font_path}, using default font.")
        font = ImageFont.load_default()

    return font

def show_img(image):

    # 如果使用OpenCV加载的是BGR格式，转换为RGB格式
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # 显示图像
    plt.imshow(image_rgb)
    plt.axis('off')  # 可选：关闭坐标轴
    plt.show()


# 创建一个颜色标签类
class ColorLabeler:
    def __init__(self):
        # 初始化一个颜色词典
        colors = OrderedDict(
            {
            '橙色': (255, 153, 0),
             '灰色': (128, 128, 128),
             '粉色': (255, 179, 179),
             '紫色': (129, 0, 127),
             '红色': (255, 51, 0),
             '绿色': (51, 179, 102),
             '蓝色': (25, 129, 255),
             '黄色': (255, 255, 0)
            }
        )



        # 为LAB图像分配空间
        self.lab = np.zeros((len(colors), 1, 3), dtype="uint8")
        self.colorNames = []

        # 循环 遍历颜色词典
        for (i, (name, rgb)) in enumerate(colors.items()):
            # 进行参数更新
            self.lab[i] = rgb
            self.colorNames.append(name)

        # 进行颜色空间的变换
        self.lab = cv2.cvtColor(self.lab, cv2.COLOR_RGB2LAB)

    def label(self, image, c):
        # 根据轮廓构造一个mask，然后计算mask区域的平均值
        mask = np.zeros(image.shape[:2], dtype="uint8")
        cv2.drawContours(mask, [c], -1, 255, -1)
        mask = cv2.erode(mask, None, iterations=2)
        mean = cv2.mean(image, mask=mask)[:3]

        # 初始化最小距离
        minDist = (np.inf, None)

        # 遍历已知的LAB颜色值
        for (i, row) in enumerate(self.lab):
            # 计算当前l*a*b*颜色值与图像平均值之间的距离
            d = dist.euclidean(row[0], mean)

            # 如果当前的距离小于最小的距离，则进行变量更新
            if d < minDist[0]:
                minDist = (d, i)

        # 返回最小距离对应的颜色值
        return self.colorNames[minDist[1]]


# 创建形状检测类
class ShapeDetector:
    def __init__(self):
        pass

    def iseq(self, x, y):
        return x == y  or abs(x - y) == 1

    def detect(self, c):
        # 初始化形状名和近似的轮廓
        shape = "unidentified"
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)
        approx_len = len(approx)

        # 如果当前的轮廓含有3个顶点，则其为三角形
        if len(approx) == 3:
            shape = "三角形"

        # 如果当前的轮廓含有4个顶点，则其可能是矩形或者正方形
        elif len(approx) == 4:
            # 获取轮廓的边界框并计算长和宽的比例
            (x, y, w, h) = cv2.boundingRect(approx)

            ar = w / float(h)

            # 计算每条边的长度
            sides = [int(np.linalg.norm(approx[i] - approx[(i + 1) % 4])) for i in range(4)]

            # 如果相邻边长度比率不同，则是梯形
            if self.iseq(sides[0], sides[2]) and sides[1] > sides[3]:
                shape = "梯形"
                return shape
            elif self.iseq(sides[0], sides[2]) and sides[0] != sides[1]:
                shape = "长方形"
            else:
                shape = "正方形"

        elif len(approx) == 6:
            shape = "多边形"

        elif len(approx) == 7:
            shape = "圆环"

        elif len(approx) == 8:
            shape = "圆形"

        # 如果这个轮廓含有5个顶点，则它是一个五角星或者其他多边形
        elif len(approx) == 10:
            shape = "五角星"

        # 如果当前轮廓的点数接近圆形
        else:
            area = cv2.contourArea(c)
            circle_ratio = area / (peri * peri / (4 * np.pi))
            # 设定一个阈值，例如0.85，来判断是否为圆形
            if circle_ratio >= 0.85:
                shape = "圆形"
            else:
                shape = "圆环"

        return shape


cl = ColorLabeler()
sd = ShapeDetector()
ocr = PaddleOCR(use_angle_cls=False, lang="ch", show_log=False)

def get_tips(tip_image_path):
    result = ocr.ocr(tip_image_path, cls=False)
    try:
        text = result[0][0][1][0]
    except:
        return

    if color_re.search(text):
        text = color_re.search(text).group(1)
    elif shape_re.search(text):
        text = shape_re.search(text).group(1)
    return text


def get_X_Y(cpc_image_path, tip_image_path):
    tip = get_tips(tip_image_path)
    if not tip:
        return

    image = cv2.imread(cpc_image_path)

     # 显示原始图像
    # display(Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)))
    # show_img(image)

    # 进行高斯模糊操作
    blurred = cv2.GaussianBlur(image, (1, 1), 0)

    # 显示模糊后的图像
    # display(Image.fromarray(cv2.cvtColor(blurred, cv2.COLOR_BGR2RGB)))
    # show_img(image)

    # 进行颜色空间的变换
    lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB)

    # 图像灰度化
    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)

    # 显示灰度图像
    # display(Image.fromarray(gray, 'L'))
    # show_img(gray)

    # 阈值分割
    _, thresh = cv2.threshold(gray, 210, 255, cv2.THRESH_BINARY)

    # display(Image.fromarray(cv2.cvtColor(thresh, cv2.COLOR_BGR2RGB)))

    # 显示二值化图像
    # display(Image.fromarray(thresh, 'L'))
    # show_img(thresh)

    # 寻找轮廓
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    cnts_list = []

    X, Y = None, None

    for i, c in enumerate(cnts):
        # 计算轮廓的中心点
        M = cv2.moments(c)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            color = cl.label(lab, c)

            try:
                shape = sd.detect(c)
            except Exception as e:
                shape = None

            if tip in (color, shape):
                X, Y = cX, cY

            # 以下是debug 代码
            # 绘制轮廓中心点
            cv2.circle(image, (cX, cY), 5, (255, 0, 0), -1)

            # 在原图上标记中心点位置
            cv2.putText(image, f'({cX}, {cY})', (cX - 50, cY - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 2)


            cnts_list.append({
                "color": color,
                "shape": shape,
                "cX": cX,
                "cY": cY,
                # "image": copy.deepcopy(image)
            })
            # 显示带标记的原始图像
            # display(Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)))
            # show_img(image)

            # 输出信息
            # print(f"{i } cX = {cX}, cY = {cY}, tip = {tip} color = {color}, shape = {shape}")


    return {
        "tip": tip,
        "cnts_list": cnts_list,
        "X": X,
        "Y": Y
    }


if __name__ == "__main__":

    p1 = '/Users/orange/workspace/jd_wskey/images/20240603152808_cpc.jpg'
    p2 = '/Users/orange/workspace/jd_wskey/images/20240603152808_tip_screenshot.png'

    res = get_X_Y(p1, p2)

    for cnts in res['cnts_list']:
        print(f"{cnts['shape']}, {cnts['color']}, {cnts['cX']}, {cnts['cY']}")
        show_img(cnts["image"])
        plt.pause(0.5)

    print(res['X'], res['Y'])
