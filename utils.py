import functools
import time
import traceback

TRY_TIMES = 5


def try_many_times(fail_exit=False, times=TRY_TIMES):
    def decorate(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    time.sleep(i * 1 + 1)
                    print(f"try {i} times. Get err")
                    traceback.print_exc()

            if fail_exit:
                raise Exception(f"重试错误")

        return wrapper

    return decorate


async def get_cookies(qinglong):
    envs = qinglong.get_env()
    return list(filter(lambda x: "name" in x and x["name"] == "JD_COOKIE", envs))
