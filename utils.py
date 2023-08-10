import datetime
import functools
import logging
import os
import sys
import time
import traceback
from logging import handlers

import colorlog
import socks
from telethon import TelegramClient

TRY_TIMES = 5


def try_many_times(fail_exit=False, times=TRY_TIMES):
    def decorate(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    time.sleep(i * 1 + 1)
                    print(f"try {i} times. Get err")
                    traceback.print_exc()

            if fail_exit:
                raise Exception(f"重试错误")

        return wrapper

    return decorate


async def get_cookies(qinglong):
    envs = qinglong.get_env()
    return list(filter(lambda x: "name" in x and x["name"] == "JD_COOKIE", envs))


def get_tg_client(proxy_ip=None, proxy_port=None, session_name="tg"):
    api_id = os.environ.get("tg_api_id")
    api_hash = os.environ.get("tg_api_hash")

    if proxy_ip and proxy_port:
        client = TelegramClient(
            session_name, api_id, api_hash, proxy=(socks.SOCKS5, proxy_ip, proxy_port)
        )
    else:
        client = TelegramClient(session_name, api_id, api_hash)

    return client


log_colors_config = {
    "DEBUG": "white",  # cyan white
    "INFO": "white",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold_red",
}


def get_logger(file_name, level=logging.INFO):
    logger = logging.getLogger(file_name)
    # 防止日志重复打印 logger.propagate 布尔标志, 用于指示消息是否传播给父记录器
    logger.propagate = False

    fmt = "%(asctime)s - %(levelname)s: %(message)s"
    if not logger.handlers:
        # 1
        ch = logging.StreamHandler()

        colored_formatter = colorlog.ColoredFormatter(
            fmt=f"%(log_color)s{fmt}",
            log_colors=log_colors_config,
        )
        ch.setFormatter(colored_formatter)

        # 2
        today = datetime.datetime.today()
        today_now = f"{today:%Y-%m-%d}"
        PARENT_DIR = os.path.abspath(os.path.dirname(__file__))
        LOGGING_DIR = os.path.join(PARENT_DIR, f"logs/{file_name}")
        file_handler = handlers.TimedRotatingFileHandler(
            filename=os.path.join(LOGGING_DIR, today_now),
            when="D",
            interval=1,
            backupCount=15,
        )
        file_handler.suffix = ".log"
        file_formatter = logging.Formatter(fmt)
        file_handler.setFormatter(file_formatter)

        logger.setLevel(level)
        logger.addHandler(ch)
        logger.addHandler(file_handler)
    return logger


# if __name__ == '__main__':
#     logger = Logger("测试").logger
#     logger.debug('debug')
#     logger.info('info')
#     logger.warning('warning')
#     logger.error('error')
#     logger.critical('critical')
