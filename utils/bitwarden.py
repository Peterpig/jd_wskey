import json
import subprocess
from utils.utils import get_logger

logger = get_logger(__file__.replace('.py', ''))

def get_username_passwd_from_bit(bit_id):
    try:
        out_bytes = subprocess.check_output(
            ["/usr/local/bin/bw", "get", "item", bit_id]
        )
    except subprocess.CalledProcessError as e:
        logger.error("获取bit信息失败1！！")
        raise e

    try:
        info = json.loads(out_bytes.decode())
        login = info["login"]
        return login["username"], login["password"]
    except (KeyError, ValueError) as e:
        logger.error("解析bit信息失败2！！, ", out_bytes)
        raise e