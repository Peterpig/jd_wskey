import asyncio
import datetime
import re
import signal
import sys
from collections import defaultdict

import aiohttp
import yaml
from telethon import events

from qinglong import init_ql
from utils.utils import get_logger, get_tg_client

CONFIG_URL = "https://p.6tun.com/https://raw.githubusercontent.com/shufflewzc/AutoSpy/master/config/Faker.spy"

ql = init_ql()
config_map = {}
task_id_map = defaultdict(list)
task_name_map = defaultdict(list)


logger = get_logger(__file__)


async def refresh():
    global task_id_map
    global task_name_map
    task_id_map = defaultdict(list)
    task_name_map = defaultdict(list)
    await asyncio.gather(get_all_task(), get_parse_config())


async def get_parse_config():
    global config_map
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(CONFIG_URL) as r:
            config = await r.text()
            config = yaml.load(config, Loader=yaml.FullLoader)
            js_config = config["js_config"]
            for config in js_config:
                env = config["Env"]
                config_map[env] = config
    logger.info("刷新config成功")


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
    logger.info("刷新task成功")


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
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %f")
    raw_text_lines = raw_text.splitlines()

    try:
        act_name = raw_text_lines[0]
        pattern = re.compile(r"[^\u4e00-\u9fa5]")
        act_name = act_name.split("·")[0]
        act_name = re.sub(pattern, "", act_name)
    except Exception as e:
        act_name = None

    env_list = []

    try:
        env_str_list = raw_text_lines[1:]
        for env_str in env_str_list:
            env_name, value = await parse_env(env_str)
            if not env_name:
                continue

            env_list.append(
                {
                    "name": env_name,
                    "value": value,
                    "remarks": f"[AutoGen]-[{now}]",
                }
            )
    except Exception as e:
        pass

    logger.info(f"获取到环境变量：{env_list}")
    return env_list, act_name

async def auto_delet_env():
    # 接收消息时，为5的倍数，清理一次
    if datetime.datetime.now().hour / 5 != 0:
        return

    envlist = ql.get_env()
    auto_gen_env = list(filter(lambda x: 'remarks' in x and '[AutoGen]-' in x['remarks'], envlist))
    if auto_gen_env:
        await asyncio.sleep(60 * 5)
        env_id = [x['id'] for x in auto_gen_env]
        logger.info(f"删除环境变量")
        ql.delete_env(env_id)

async def handler(event):
    raw_text = event.raw_text
    logger.info(f"检测到消息 \n{raw_text}")

    env_list, act_name = await parse_message(raw_text)
    if not env_list:
        return

    await event.message.mark_read()

    tasks = []
    for env in env_list:
        env_name = env["name"]
        value = env["value"]

        exist_env = await env_exist(env_name)
        if not exist_env:
            logger.info(f"环境变量【{env_name}】不存在，插入！")
            ret = ql.insert_env([env])
            env_id = ret[0]["id"]
        else:
            if value != exist_env["value"]:
                logger.info(f"环境变量【{env_name}】存在，且不一致，更新！")
                env_id = exist_env["id"]
                env["id"] = env_id
                ret = ql.put_env(env)

        if env_name in config_map:
            logger.warning(f"环境变量【{env_name}】在配置文件中")

            task_info = config_map[env_name]
            script = task_info["Script"]
            if script not in task_id_map:
                logger.warning(f"环境变量【{env_name}】task配置中, 跳过")
                continue

            tasks.extend(task_id_map[script])

    if act_name:
        for k, v in task_name_map.items():
            if act_name in k:
                tasks.extend(v)

    if not tasks:
        logger.warning(f"环境变量【{env_name}】没找到可执行任务，跳过")
        return

    task_names = list(map(lambda x: x["name"], tasks))
    task_ids = list(map(lambda x: x["id"], tasks))

    logger.info(f"开始运行脚本【{', '.join(task_names)}】")
    ql.run_crons(task_ids)

    await asyncio.sleep(60)
    logger.info(f"消息处理完毕\n")

    await refresh()
    await auto_delet_env()


async def main():
    global config_map
    await refresh()

    tg_logger = get_logger("tg", console=False)
    client = get_tg_client(proxy_ip="127.0.0.1", proxy_port=7890, logger=tg_logger)

    async with client:
        me = (await client.get_me()).username
        logger.info(me)

        client.add_event_handler(
            handler, events.NewMessage(pattern=r".*\n*export \w+=\"[^\"]+\"")
        )

        await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
