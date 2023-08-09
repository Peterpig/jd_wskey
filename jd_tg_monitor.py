import asyncio
import datetime
import logging
from collections import defaultdict
from concurrent.futures._base import CancelledError

import aiohttp
import yaml
from telethon import events

from qinglong import init_ql
from utils import get_tg_client

CONFIG_URL = "https://p.6tun.com/https://raw.githubusercontent.com/shufflewzc/AutoSpy/master/config/Faker.spy"

ql = init_ql()
config_map = {}
task_map = defaultdict(list)


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def refresh():
    await get_all_task()
    await get_parse_config()


async def get_parse_config():
    global config_map
    async with aiohttp.ClientSession() as session:
        async with session.get(CONFIG_URL) as r:
            config = await r.text()
            config = yaml.load(config, Loader=yaml.FullLoader)
            js_config = config["js_config"]
            for config in js_config:
                env = config["Env"]
                config_map[env] = config


async def get_all_task():
    global task_map
    all_task = ql.crons()["data"]
    for task in all_task:
        id = task["id"]
        command = task["command"]
        scrpit = command.split("/")[-1]
        task_map[scrpit].append(id)


async def env_exist(env_name):
    envlist = ql.get_env()
    envlist = list(filter(lambda x: "name" in x and x["name"] == env_name, envlist))
    if envlist:
        return envlist[0]

    return False


# @client.on(events.NewMessage)


async def main():
    global config_map
    await refresh()

    client = get_tg_client(proxy_ip="127.0.0.1", proxy_port=7890)

    async with client:
        me = (await client.get_me()).username
        print(me)

        @client.on(events.NewMessage(pattern=r"export \w+=\"[^\"]+\""))
        async def handler(event):
            raw_text = event.raw_text
            logging.info(f"检测到消息 {raw_text}")
            raw_text_lines = raw_text.splitlines()

            name, value = None, None
            for raw_text in raw_text_lines:
                try:
                    name = raw_text.split(" ", 1)[1].split("=", 1)[0]
                    value = raw_text.split(" ", 1)[1].split("=", 1)[1][1:-1]
                    break
                except Exception:
                    pass

            if not (name and value):
                return

            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %f")
            env = {
                "name": name,
                "value": value,
                "remarks": f"[AutoGen]-[{now}]",
            }
            logging.info(f"获取到环境变量：{env}")
            if name not in config_map:
                logging.warn(f"环境变量{name} 不在配置文件中, 跳过")
                return

            task_info = config_map[name]
            task = task_info["Script"]
            if task not in task_map:
                logging.warn(f"环境变量{name} task配置中, 跳过")
                return

            logging.info(f"开始检测环境变量【{name}】是否存在")
            exist_env = await env_exist(name)
            if not exist_env:
                logging.info(f"环境变量{name}不存在，插入！")
                ret = ql.insert_env([env])
                env_id = ret[0]["id"]
            else:
                env_id = exist_env["id"]

            ids = task_map[task]
            logging.info(f"开始运行脚本{task_info}")
            ql.run_crons(ids)

            await asyncio.sleep(60)
            logging.info(f"删除环境变量{name}")
            ql.delete_env(env_id)
            logging.info(f"消息处理完毕\n")

        while client.is_connected():
            try:
                await client.run_until_disconnected()
            except CancelledError:
                ...
            except Exception:
                ...
        else:
            try:
                await client.connect()
            except OSError:
                print("Failed to connect")
            await asyncio.sleep(1)


if __name__ == "__main__":
    # with client:
    #     client.loop.run_until_complete(main())
    #     try:
    #         client.run_until_disconnected()
    #     except asyncio.CancelledError:
    #         ...
    #     finally:
    #         await asyncio.sleep(2)
    asyncio.run(main())
