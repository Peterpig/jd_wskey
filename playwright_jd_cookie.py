import asyncio
import json
import logging
from datetime import datetime
from playwright.async_api import async_playwright

# 导入青龙相关模块
try:
    from qinglong import Qinglong
    QINGLONG_AVAILABLE = True
except ImportError:
    QINGLONG_AVAILABLE = False
    print("警告: 青龙模块未安装")

# 导入ENV_KEEP_KEYS
try:
    from auto_set_jd_cookie import ENV_KEEP_KEYS
except ImportError:
    ENV_KEEP_KEYS = {"id", "value", "name", "remarks"}

class JDPlaywrightLogin:
    def __init__(self):
        self.cookies = {}
        self.pt_key = ""
        self.pt_pin = ""
        self.pt_st = ""

    async def get_jd_cookies(self, account_name="", qinglong_config=None):
        """使用Playwright获取京东cookie"""
        try:
            async with async_playwright() as p:
                # 启动浏览器，设置为非无头模式，方便用户看到登录过程
                browser = await p.chromium.launch(
                    headless=False,  # 显示浏览器窗口
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )

                # 创建上下文
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )

                page = await context.new_page()

                # 访问京东登录页面
                print(f"正在打开京东登录页面...")
                await page.goto("https://plogin.m.jd.com/login/login")

                # 等待用户扫码登录
                print(f"请在浏览器中扫码登录京东账号...")

                # 等待登录成功，检测URL变化
                try:
                    print("等待登录成功...")

                    # 等待跳转到m.jd.com
                    await page.wait_for_url("https://m.jd.com/", timeout=180000)
                    print("检测到跳转到m.jd.com，等待页面加载...")

                    # 等待页面完全加载
                    await page.wait_for_timeout(3000)

                    # 检查是否有commonNav元素
                    try:
                        await page.wait_for_selector("#commonNav", timeout=10000)
                        print("检测到commonNav元素，登录成功！")
                    except Exception as e:
                        print(f"未检测到commonNav元素: {str(e)}")
                        # 尝试其他可能的导航元素
                        try:
                            await page.wait_for_selector(".nav", timeout=5000)
                            print("检测到.nav元素，登录成功！")
                        except Exception:
                            print("警告：未检测到导航元素，可能登录不完整")

                    # 等待更长时间确保cookie已经设置
                    print("等待cookie设置...")
                    await page.wait_for_timeout(5000)

                except Exception as e:
                    print(f"等待登录超时或失败: {str(e)}")
                    await browser.close()
                    return None

                # 获取所有cookie
                all_cookies = await context.cookies()
                print(f"获取到 {len(all_cookies)} 个cookie")

                # 筛选京东相关的cookie
                jd_cookies = {}
                for cookie in all_cookies:
                    domain = cookie.get('domain', '')
                    name = cookie.get('name', '')
                    value = cookie.get('value', '')

                    # 打印所有cookie用于调试
                    print(f"Cookie: {name} = {value[:20]}... (domain: {domain})")

                    if any(domain_pattern in domain for domain_pattern in ['.jd.com', 'jd.com']):
                        jd_cookies[name] = value

                print(f"筛选出 {len(jd_cookies)} 个京东相关cookie")

                # 提取关键cookie
                self.pt_key = jd_cookies.get('pt_key', '')
                self.pt_pin = jd_cookies.get('pt_pin', '')
                self.pt_st = jd_cookies.get('pt_st', self.pt_key)  # 如果没有pt_st，用pt_key代替

                # 检查是否获取到关键cookie
                if not self.pt_key or not self.pt_pin:
                    print("警告：未获取到关键的pt_key或pt_pin")
                    print("尝试从页面直接获取cookie...")

                    # 尝试从页面直接获取cookie
                    try:
                        page_cookies = await page.evaluate("""
                            () => {
                                return document.cookie;
                            }
                        """)
                        print(f"页面cookie: {page_cookies}")
                    except Exception as e:
                        print(f"获取页面cookie失败: {str(e)}")

                # 构建完整的cookie数据
                cookie_data = {
                    "pt_key": self.pt_key,
                    "pt_pin": self.pt_pin,
                    "pt_st": self.pt_st,
                    "username": account_name or self.pt_pin,
                    "__time": str(datetime.now().timestamp()),
                    "all_cookies": jd_cookies
                }

                print(f"获取到的cookie:")
                print(f"pt_key: {self.pt_key[:20]}..." if len(self.pt_key) > 20 else f"pt_key: {self.pt_key}")
                print(f"pt_pin: {self.pt_pin}")
                print(f"pt_st: {self.pt_st[:20]}..." if len(self.pt_st) > 20 else f"pt_st: {self.pt_st}")

                await browser.close()

                # 如果配置了青龙面板，尝试存储cookie
                if qinglong_config and QINGLONG_AVAILABLE:
                    try:
                        await self.save_to_qinglong(cookie_data, account_name, qinglong_config)
                    except Exception as e:
                        print(f"保存到青龙面板失败: {str(e)}")

                return cookie_data

        except Exception as e:
            print(f"获取cookie失败: {str(e)}")
            logging.error(f"Playwright获取cookie失败: {str(e)}")
            return None

    async def save_to_qinglong(self, cookie_data, account_name, qinglong_config):
        """保存cookie到青龙面板"""
        try:
            print("正在保存cookie到青龙面板...")

            # 创建青龙实例
            ql = Qinglong(qinglong_config)

            # 获取现有环境变量
            envlist = ql.get_env()

            # 构造cookie字符串
            cookie_str = f"pt_key={cookie_data['pt_key']};pt_pin={cookie_data['pt_pin']};pt_st={cookie_data['pt_st']};"

            # 查找是否已存在该账户的cookie
            existing_env = None
            for env in envlist:
                if env.get("name") == "JD_COOKIE" and cookie_data['pt_pin'] in env.get("value", ""):
                    existing_env = env
                    break

            if existing_env:
                # 更新现有cookie
                existing_env["value"] = cookie_str
                # existing_env["remarks"] = f"{account_name}(自动更新)"
                # 只保留 ENV_KEEP_KEYS 字段
                filtered_env = {k: v for k, v in existing_env.items() if k in ENV_KEEP_KEYS}
                print(f"filtered_env === {filtered_env}")
                ql.set_env(data=filtered_env)
                print(f"更新青龙面板cookie成功: {account_name}")
            else:
                # 新增cookie
                new_env = {
                    "value": cookie_str,
                    "name": "JD_COOKIE",
                    "remarks": f"{account_name}(自动新增)",
                }
                ql.insert_env(data=[new_env])
                print(f"新增青龙面板cookie成功: {account_name}")

        except Exception as e:
            print(f"保存到青龙面板失败: {str(e)}")
            raise e

async def main():
    """测试函数"""
    login = JDPlaywrightLogin()
    result = await login.get_jd_cookies("测试账号")
    if result:
        print("Cookie获取成功！")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Cookie获取失败！")

if __name__ == "__main__":
    asyncio.run(main())