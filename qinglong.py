import json
import logging
from typing import List

import requests
from retry import retry

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)
TRY_TIMES = 10


class Qinglong:
    def __init__(self, json_config):
        self.host = f"{json_config['host']}"
        self.client_id = json_config["client_id"]
        self.client_secret = json_config["client_secret"]
        self.token = None
        self.task_id = []

        self.header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36 Edg/94.0.992.38",
        }
        Qinglong.gen_token(self)

    @staticmethod
    def gen_token(cls):
        url = cls.host + "/open/auth/token"
        data = {"client_id": cls.client_id, "client_secret": cls.client_secret}
        response = cls.request_method("get", url, data)
        try:
            cls.token = response["token"]
        except KeyError:
            raise KeyError(f"获取token失败")

        if cls.token:
            cls.header.update({"Authorization": f"Bearer {cls.token}"})

    @retry(tries=TRY_TIMES, delay=2)
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
            self.enable_env(response["id"])
        return response

    def enable_env(self, env_ids: List[str]):
        url = self.host + "/open/envs/enable"
        if not isinstance(env_ids, list):
            env_ids = [env_ids]

        env_ids = [str(x) for x in env_ids if x]
        response = self.request_method("put", url, data=env_ids)
        return response
