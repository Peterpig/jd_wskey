import datetime
import functools
import logging
import os
import sys
import time
import traceback
from logging import handlers
from pathlib import Path

import colorlog
import socks
from telethon.sync import TelegramClient

TRY_TIMES = 3


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


def get_tg_client(proxy_ip='127.0.0.1', proxy_port=7890, session_name="tg", logger=None):
    api_id = os.environ.get("tg_api_id")
    api_hash = os.environ.get("tg_api_hash")

    if proxy_ip and proxy_port:
        client = TelegramClient(
            session_name,
            api_id,
            api_hash,
            proxy=(socks.SOCKS5, proxy_ip, proxy_port),
            base_logger=logger,
        )
    else:
        client = TelegramClient(session_name, api_id, api_hash, base_logger=logger)
    return client


log_colors_config = {
    "DEBUG": "white",  # cyan white
    "INFO": "white",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold_red",
}


def get_logger(file_name, level=logging.INFO, console=True, rotating=True):
    logger = logging.getLogger(file_name)
    # 防止日志重复打印 logger.propagate 布尔标志, 用于指示消息是否传播给父记录器
    logger.propagate = False

    fmt = "%(asctime)s - %(levelname)s: %(message)s"
    if not logger.handlers:
        if console:
            # 1
            ch = logging.StreamHandler()

            colored_formatter = colorlog.ColoredFormatter(
                fmt=f"%(log_color)s{fmt}",
                log_colors=log_colors_config,
            )
            ch.setFormatter(colored_formatter)
            logger.addHandler(ch)

        if rotating:
            # 2
            today = datetime.datetime.today()
            today_now = f"{today:%Y-%m-%d}"
            PARENT_DIR = os.path.abspath(os.path.dirname(__file__))
            LOGGING_DIR = os.path.join(PARENT_DIR, f"logs/{file_name}")
            Path(LOGGING_DIR).mkdir(parents=True, exist_ok=True)
            file_handler = handlers.TimedRotatingFileHandler(
                filename=os.path.join(LOGGING_DIR, "log"),
                when="D",
                interval=1,
                backupCount=15,
            )
            file_handler.suffix = "%Y-%m-%d.log"
            file_formatter = logging.Formatter(fmt)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        logger.setLevel(level)

    return logger





# if __name__ == '__main__':
#     logger = Logger("测试").logger
#     logger.debug('debug')
#     logger.info('info')
#     logger.warning('warning')
#     logger.error('error')
#     logger.critical('critical')
