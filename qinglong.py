import json
import logging
import os
import sys
from typing import Dict, List

import requests
from retry import retry

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)
TRY_TIMES = 20


class Qinglong:
    # openapi地址
    # https://qinglong.ukenn.top/
    def __init__(self, json_config):
        # 必须包含'host', 'client_id', 'client_secret'
        # 或包含 'token'
        if (
            set(["host", "client_id", "client_secret"]) - set(json_config.keys())
            != set()
        ) and not json_config.get("token"):
            raise Exception("参数错误， 请传入token或认证信息")

        self.host = json_config.get("host")
        self.client_id = json_config.get("client_id")
        self.client_secret = json_config.get("client_secret")
        self.token = json_config.get("token")
        self.task_id = []

        self.header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36 Edg/94.0.992.38",
        }

        if not self.token:
            Qinglong.gen_token(self)

        if not self.token:
            raise Exception("Token生成错误!")

        self.header.update({"Authorization": f"Bearer {self.token}"})

    @staticmethod
    def gen_token(cls):
        url = cls.host + "/open/auth/token"
        data = {"client_id": cls.client_id, "client_secret": cls.client_secret}
        response = cls.request_method("get", url, data)
        try:
            cls.token = response["token"]
        except KeyError:
            raise KeyError(f"获取token失败")

    @retry(tries=TRY_TIMES, delay=2, backoff=2)
    def request_method(self, method, url, params=None, data=None):
        try:
            kwargs = {"timeout": 30, "headers": self.header}
            if data:
                kwargs["data"] = json.dumps(data)
            if params:
                kwargs["params"] = params

            response = requests.request(method=method, url=url, **kwargs)
            response_json = response.json()
        except Exception as e:
            logging.error(f"访问青龙接口{url}失败，请确保青龙已经正常启动！")
            raise Exception(e)

        if ("code" not in response_json) or (response_json["code"] != 200):
            raise Exception(f"请求{url}失败: {response_json}")

        return response_json["data"] if "data" in response_json else None

    def get_env(self):
        url = self.host + "/open/envs"
        response = self.request_method("get", url)
        return response

    def set_env(self, data):
        url = self.host + "/open/envs"
        response = self.request_method("put", url, data=data)
        self.enable_env(response["id"])
        return response

    def insert_env(self, data):
        url = self.host + "/open/envs"
        response = self.request_method("post", url, data=data)
        if response:
            if isinstance(response, list):
                for r in response:
                    self.enable_env(r["id"])
            else:
                self.enable_env(response["id"])
        return response

    def put_env(self, data):
        url = self.host + "/open/envs"
        response = self.request_method("put", url, data=data)
        if response:
            if isinstance(response, list):
                for r in response:
                    self.enable_env(r["id"])
            else:
                self.enable_env(response["id"])
        return response

    def delete_env(self, env_ids: List[str]):
        url = self.host + "/open/envs"
        if not isinstance(env_ids, list):
            env_ids = [env_ids]

        env_ids = [str(x) for x in env_ids if x]
        response = self.request_method("delete", url, data=env_ids)
        return response

    def enable_env(self, env_ids: List[str]):
        url = self.host + "/open/envs/enable"
        if not isinstance(env_ids, list):
            env_ids = [env_ids]

        env_ids = [str(x) for x in env_ids if x]
        response = self.request_method("put", url, data=env_ids)
        return response

    def disable_env(self, env_ids: List[str]):
        url = self.host + "/open/envs/disable"
        if not isinstance(env_ids, list):
            env_ids = [env_ids]

        env_ids = [str(x) for x in env_ids if x]
        response = self.request_method("put", url, data=env_ids)
        return response

    def enable_task(self, task_ids: List[str]):
        url = self.host + "/open/crons/enable"
        if not isinstance(task_ids, list):
            task_ids = [task_ids]

        task_ids = [str(x) for x in task_ids if x]
        response = self.request_method("put", url, data=task_ids)
        return response

    def crons(self):
        url = self.host + "/open/crons"
        response = self.request_method("get", url)
        return response

    def create_crons(self, data):
        url = self.host + "/open/crons"
        response = self.request_method("post", url, data=data)
        return response

    def run_crons(self, task_ids: List[str]):
        url = self.host + "/open/crons/run"

        task_ids = [str(x) for x in task_ids if x]
        response = self.request_method("put", url, data=task_ids)
        return response

    def put_cron(self, task_info: Dict[str, str]):
        """
            task_info = {
                "name": "大牌1220",
                "command": "task 6dylan6_jdpro/jd_dplh1220.js",
                "schedule": "1 1,18 * * *",
                "extra_schedules": null,
                "labels": [],
                "task_before": null,
                "task_after": null,
                "id": 6826
            }
        """
        url = self.host + "/open/crons"
        response = self.request_method("put", url, data=task_info)
        return response


def init_ql():
    host = os.environ.get("host")
    client_id = os.environ.get("client_id")
    client_secret = os.environ.get("client_secret")

    if not (host and client_id and client_secret):
        logger.error("请设置青龙环境环境变量 host、client_id、client_secret!")
        sys.exit(0)

    json_config = {"host": host, "client_id": client_id, "client_secret": client_secret}

    qinglong = Qinglong(json_config)
    return qinglong
