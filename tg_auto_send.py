"""
new Env('tg农场助理池子');
cron: 30 23 * * 0 tg_auto_send.py
"""

import os

from utils import get_tg_client


async def main(client):
    texts = [
        (
            "chriszhuli_bot",
            "/farm 37a42e0be3a24bc493b397ae50ff07cf&3e82c57246db4331a60bb91755b68e08&a6152559c2df4b57bfb2cefd4916ab91&155380a3d9834e9b9814bed1d4d20b00&a7b1c06cc6874e559952e3f88031b0e1",
        ),
        (
            "chriszhuli_bot",
            "/bean yj35hqk6ip2sszfd5jxckh54nm&4npkonnsy7xi2sihztxeqryq3gxmk5cqrby26qq&kidjksa67jjv5lfj2vicj275me5ac3f4ijdgqji&4srjlxwmo6kapro6uookyfafoiuky2f2gwzew5y&4npkonnsy7xi2c5ti74jv5fnibdhqwxlnoqlpdq&ebxm5lgxoknqck745mm3flhirnosa6pgc34arfi",
        ),
    ]

    for text in texts:
        await client.send_message(text[0], text[1])


if __name__ == "__main__":
    client = get_tg_client()

    with client:
        client.loop.run_until_complete(main(client))
