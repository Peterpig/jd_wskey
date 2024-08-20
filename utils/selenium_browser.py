import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException

# Constants
BROWSER_TYPE = "Chrome"
HEADLESS = False
WINDOW_SIZE = (500, 700)
DRIVER_PATHS = {
    "darwin": "./drivers/chromedriver123.0.6312.87",
    "win32": "./drivers/chromedriver",
}

def get_file(file_name: str = "") -> str:
    """
    获取文件绝对路径, 防止在某些情况下报错
    :param file_name: 文件名
    :return: 文件的绝对路径
    """
    print(f"11 = {os.path.abspath(__file__)}")
    print(f"22 = {os.path.dirname(os.path.abspath(__file__))}")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), file_name)

def log_error(message: str) -> None:
    """
    打印错误信息
    :param message: 错误信息
    """
    print(f"\r[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}] [ERROR] {message}")

def get_browser(path_prefix: str = "") -> webdriver.Chrome:
    """
    获取浏览器对象
    :return: Selenium WebDriver 对象
    """
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--incognito")  # 无痕模式
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])

    if HEADLESS:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")

    try:

        driver_path = get_file(path_prefix + DRIVER_PATHS[sys.platform]) if sys.platform in DRIVER_PATHS else None
        # 使用 Service 对象来指定 ChromeDriver 的路径
        service = Service(executable_path=driver_path) if driver_path else None
        _browser_ = webdriver.Chrome(service=service, options=chrome_options)
        _browser_.set_window_size(*WINDOW_SIZE)
        return _browser_
    except WebDriverException as e:
        handle_webdriver_exception(e)

def handle_webdriver_exception(e: WebDriverException) -> None:
    """
    处理 WebDriver 异常
    :param e: WebDriverException 实例
    """
    error_messages = {
        "This version of ChromeDriver only supports Chrome version": "浏览器错误(chromedriver版本错误)，请比对前三位版本号",
        "'chromedriver' executable needs to be in PATH": "浏览器错误，请检查你下载并解压好的驱动是否放在drivers目录下",
        "unknown error: cannot find Chrome binary": "浏览器错误(Chrome浏览器可执行文件路径未成功识别)，请在配置文件中修改selenium.binary为浏览器可执行文件绝对路径"
    }

    for key, message in error_messages.items():
        if key in str(e):
            log_error(message)
            break
    else:
        log_error(f"浏览器错误， 请检查你下载并解压好的驱动是否放在drivers目录下，如需帮助请及时反馈; err: {str(e)}")

    raise e
