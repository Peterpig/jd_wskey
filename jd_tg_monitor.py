import datetime

from telethon import events

from qinglong import init_ql
from utils import get_tg_client


async def handler(event):
    message = event.message
    raw_text = event.raw_text

    try:
        name = raw_text.split(" ", 1)[1].split("=", 1)[0]
        value = raw_text.split(" ", 1)[1].split("=", 1)[1][1:-1]
    except Exception:
        return

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %f")
    env = {
        "name": name,
        "value": value,
        "remark": f"[AutoGen]-[{now}]-[{event.from_id}])",
    }
    event.reply_markup()
    ql.insert_env(env)


if __name__ == "__main__":
    client = get_tg_client(proxy_ip="127.0.0.1", proxy_port=7890)
    client.start()
    ql = init_ql()
    newmsg = events.NewMessage(pattern=r"export \w+=\"[^\"]+\"")
    client.add_event_handler(handler, newmsg)
    client.run_until_disconnected()
