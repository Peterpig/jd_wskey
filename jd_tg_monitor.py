import asyncio
import datetime
import logging
import re
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
task_id_map = defaultdict(list)
task_name_map = defaultdict(list)


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
    global task_id_map
    global task_name_map
    all_task = ql.crons()["data"]
    for task in all_task:
        id = task["id"]
        name = task["name"]
        command = task["command"]
        scrpit = command.split("/")[-1]
        task_id_map[scrpit].append(task)
        task_name_map[name].append(task)


async def env_exist(env_name):
    envlist = ql.get_env()
    envlist = list(filter(lambda x: "name" in x and x["name"] == env_name, envlist))
    if envlist:
        return envlist[0]

    return False


async def parse_env(env_str):
    try:
        env_name = env_str.split(" ", 1)[1].split("=", 1)[0]
        value = env_str.split(" ", 1)[1].split("=", 1)[1][1:-1]
        return env_name, value
    except Exception as e:
        raise e


async def parse_message(raw_text):
    raw_text_lines = raw_text.splitlines()

    act_name = None
    if len(raw_text_lines) == 2:
        act_name = raw_text_lines[0]
        env_str = raw_text_lines[1]

        try:
            env_name, value = await parse_env(env_str)

            pattern = re.compile(r"[^\u4e00-\u9fa5]")
            act_name = act_name.split("·")[0]
            act_name = re.sub(pattern, "", act_name)
        except Exception:
            return None, None
    else:
        for env_str in raw_text_lines:
            env_name, value = await parse_env(env_str)
            if env_name:
                break

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %f")
    env = {
        "name": env_name,
        "value": value,
        "remarks": f"[AutoGen]-[{now}]",
    }
    logging.info(f"获取到环境变量：{env}")
    return env, act_name


async def main():
    global config_map
    await refresh()

    client = get_tg_client(proxy_ip="127.0.0.1", proxy_port=7890)

    async with client:
        me = (await client.get_me()).username
        print(me)

        @client.on(events.NewMessage(pattern=r".*\n*export \w+=\"[^\"]+\""))
        async def handler(event):
            raw_text = event.raw_text
            logging.info(f"检测到消息 {raw_text}")

            env, act_name = await parse_message(raw_text)
            if not env:
                return

            env_name = env["name"]

            logging.info(f"开始检测环境变量：【{env_name}】是否存在")
            exist_env = await env_exist(env_name)
            if not exist_env:
                logging.info(f"环境变量【{env_name}】不存在，插入！")
                ret = ql.insert_env([env])
                env_id = ret[0]["id"]
            else:
                logging.info(f"环境变量【{env_name}】存在，更新！")
                env_id = exist_env["id"]
                env["id"] = env_id
                ret = ql.put_env(env)

            tasks = []
            if env_name in config_map:
                logging.warning(f"环境变量【{env_name}】在配置文件中")

                task_info = config_map[env_name]
                script = task_info["Script"]
                if script not in task_id_map:
                    logging.warning(f"环境变量【{env_name}】task配置中, 跳过")
                    return

                tasks = task_id_map[script]

            if act_name:
                for k, v in task_name_map.items():
                    if act_name in k:
                        tasks.extend(v)

            if not tasks:
                logging.warning(f"环境变量【{env_name}】没找到可执行任务，跳过")
                return

            task_names = list(map(lambda x: x["name"], tasks))
            task_ids = list(map(lambda x: x["id"], tasks))

            logging.info(f"开始运行脚本{', '.join(task_names)}")
            ql.run_crons(task_ids)

            await asyncio.sleep(60)
            # logging.info(f"删除环境变量{name}")
            # ql.delete_env(env_id)
            logging.info(f"消息处理完毕\n")

        while client.is_connected():
            try:
                await client.run_until_disconnected()
            except CancelledError:
                pass
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
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
