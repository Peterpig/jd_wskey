import json
import random

import fire

from auto_set_jd_cookie import get_ck
from utils import get_logger

jd_username = ""
jd_passwd = ""
ENV_KEEP_KEYS = {"id", "value", "name", "remarks"}

#logging.basicConfig(level=logging.INFO, format="%(message)s")
#logger = logging.getLogger(__name__)
logger = get_logger(__file__.replace('.py', ''))


"""
bit_id_map.json
{
    "昵称": "bitwarden项目的id",
    "昵称2": "bitwarden项目的id",
}
"""

bit_id_map = json.load(open("./bit_id_map.json"))


async def main_local(*bit_users):
    users = json.load(open('jd_pass.json'))
    while True:
        user = random.choice(users)
        print(user)
        get_ck(*user)

if __name__ == "__main__":
    fire.Fire(main_local)
