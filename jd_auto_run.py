"""
new Env('京东青龙任务自动运行');
cron: 30 */2 * * * jd_auto_run.py
"""
import json
import logging
import os
import sys

from qinglong import init_ql

logger = logging.getLogger(__name__)

try:
    from notify import send
except:
    send = lambda *args: ...


def main():
    qinglong = init_ql()
    all_crons = qinglong.crons()

    try:
        all_task = all_crons["data"]
    except KeyError:
        logger.info("获取所有任务失败！")
        sys.exit(0)

    id_list = list(map(lambda x: x["id"], all_task))

    f = open("./auto_run.json", "a+")

    try:
        f.seek(0)
        task_json = json.load(f)
    except Exception as e:
        task_json = None

    # 历史任务不处理了
    if not task_json:
        task_json = {"old_task_ids": id_list}
        f.seek(0)
        f.truncate()
        json.dump(task_json, f, ensure_ascii=False, indent=4)
        return

    # 只对新增任务进行自动运行
    diff_task = []
    diff_ids = set(id_list) - set(task_json.get("old_task_ids", set()))
    if diff_ids:
        diff_task = list(
            filter(
                lambda x: (x["id"] in diff_ids) and task_needed_run(x),
                all_task,
            )
        )

    if not diff_task:
        logger.info("无新增任务。。。。")
        return

    logger.info(f"Run task: {', '.join(map(lambda x: x['name'], diff_task))}")
    qinglong.run_crons(map(lambda x: x["id"], diff_task))
    task_json["old_task_ids"] = id_list
    f.seek(0)
    f.truncate()
    json.dump(task_json, f, ensure_ascii=False, indent=4)
    f.close()


def task_needed_run(task_info):
    """
    task_info = {"id":2277,"name":"\u5934\u6587\u5b57JJJ","command":"task shufflewzc_faker3_main\/jd_mpdz_car.js","schedule":"33 10,19 * * *","timestamp":"Thu Jan 12 2023 17:35:29 GMT+0800 (GMT+08:00)","saved":true,"status":0,"isSystem":0,"pid":1716,"isDisabled":0,"isPinned":0,"log_path":"shufflewzc_faker3_main_jd_mpdz_car_2277\/2023-05-29-10-33-00-246.log","labels":[],"last_running_time":93,"last_execution_time":1685327580,"sub_id":null,"createdAt":"2023-01-12T09:35:29.144Z","updatedAt":"2023-05-29T02:33:00.332Z"}
    """

    try:
        if task_info["last_execution_time"] != 0:
            return False
        schedule = task_info["schedule"]
        schedule_list = schedule.split(" ")
        if len(schedule_list) == 5:
            if "*" not in schedule_list[2]:
                return True
        elif len(schedule_list) == 6:
            if "*" not in schedule_list[3]:
                return True
    except:
        return False

    return False


if __name__ == "__main__":
    main()
