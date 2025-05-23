"""
new Env('京东本地脚本自动cron');
cron: 30 */2 * * * jd_auto_local_cron.py
"""
import asyncio
import logging
import os
import random
import re
import sys
from datetime import datetime

from qinglong import Qinglong

from asyncer import asyncify
from croniter import croniter

logger = logging.getLogger(__name__)

try:
    from notify import send
except:
    send = lambda *args: ...

keep_keys = ('id', 'labels', 'name', 'command')


def init_ql():
    host = "http://127.0.0.1:5700"
    client_id = os.environ.get("local_client_id")
    client_secret = os.environ.get("local_client_secret")

    if not (host and client_id and client_secret):
        logger.error("请设置青龙环境环境变量 host、client_id、client_secret!")
        sys.exit(0)

    json_config = {"host": host, "client_id": client_id, "client_secret": client_secret}

    qinglong = Qinglong(json_config)
    return qinglong

async def main():
    qinglong = init_ql()
    all_crons = qinglong.crons()

    try:
        all_task = all_crons["data"]
    except KeyError:
        logger.info("获取所有任务失败！")
        sys.exit(0)

    msg_list = []
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    has_huizong = False
    for task in all_task:
        schedule = task["schedule"]
        command  = task["command"]
        if "jd_bean_change_huizong" in command:
            has_huizong = True

        if "BiliBiliToolPro" in command:
            continue

        schedule_list = re.sub(r' {2,}', ' ', schedule).split(' ')

        if len(schedule_list) not in (5, 6):
            continue

        # if task['id'] != 9180:
        #     continue

        # day
        day_schema = 2 if len(schedule_list) == 5 else 3
        hour_schema = 1 if len(schedule_list) == 5 else 2
        modify = False

        try:
            if schedule_list[day_schema] != "*":
                modify = True
                # 修改为每日运行
                schedule_list[-3:] = ['*'] * len(schedule_list[-3:])
                schedule_str = ' '.join(schedule_list)

                # 判断今天是不是不执行了
                cron = croniter(schedule_str, now)
                if (cron.get_next(datetime) - today).days >= 1:
                    schedule_list[hour_schema] = f'{schedule_list[hour_schema]},{now.hour + random.randint(1,3) if now.hour < 20 else now.hour}'
                    schedule_list[hour_schema] = ','.join(sorted(list(set(schedule_list[hour_schema].split(','))), key=lambda x: int(x)))

            # 每日最少执行2次
            if ("*" not in schedule_list[hour_schema]) \
                and (","  not in schedule_list[hour_schema]):
                modify = True
                if "/" in schedule_list[hour_schema]:
                    # 修改0-23/6 这种
                    schedule_list[hour_schema] = f'*/{schedule_list[hour_schema].split("/")[-1]}'
                else:
                    schedule_list[hour_schema] = f'{schedule_list[hour_schema]},{now.hour + random.randint(1,3) if now.hour < 20 else now.hour}'
                    schedule_list[hour_schema] = ','.join(sorted(list(set(schedule_list[hour_schema].split(','))), key=lambda x: int(x)))
        except Exception as e:
            logger.error(f"task: {task}, error: {e}")
            continue


        if modify:
            task_info = {k: task[k] for k in keep_keys}
            schedule_str = ' '.join(schedule_list)
            task_info['schedule'] = schedule_str

            try:
                await asyncify(qinglong.put_cron)(task_info=task_info)
            except Exception as e:
                print(f"{task_info} err: {e}")
                continue
            msg =f"{task_info['name']} - {schedule_str}"
            print(msg)
            msg_list.append(msg)

    send("京东脚本自动cron", "\n".join(msg_list))

    if not has_huizong:
        await asyncify(qinglong.create_crons)(data={

            "command": "task 6dylan6_jdpro/jd_bean_change_huizong.js",
            "schedule": "0 8,21 * * *",
            "name": "jd_bean_change_huizong",
            "labels": []

        })



if __name__ == "__main__":
    asyncio.run(main())
