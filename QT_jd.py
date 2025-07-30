import json
import logging
import os
import platform
import re
import sys
import traceback
from datetime import datetime,timezone,timedelta
import asyncio
import concurrent.futures

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qinglong import Qinglong
from jd_cookie_kill import need_login

# 导入Playwright模块
try:
    from playwright_jd_cookie import JDPlaywrightLogin
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("警告: Playwright模块未安装，将使用WebView方案")


def setup_logging():
    """设置日志"""
    try:
        # 获取用户家目录下的日志目录
        log_dir = os.path.expanduser("~/Library/Logs/JD账户管理器")
        os.makedirs(log_dir, exist_ok=True)

        # 设置日志文件名（使用当前时间）
        current_time = datetime.now()
        log_file = os.path.join(
            log_dir, f"debug_{current_time.strftime('%Y%m%d_%H%M%S')}.log"
        )

        # 确保日志文件可写
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write("=== 日志文件初始化 ===\n")
        except Exception as e:
            print(f"无法写入日志文件: {str(e)}")
            return None

        # 配置日志
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8", mode="a"),
                logging.StreamHandler(),
            ],
        )

        # 创建logger实例
        logger = logging.getLogger("JDManager")
        logger.setLevel(logging.DEBUG)

        # 添加启动信息
        logger.info("=== 应用程序启动 ===")
        logger.info(f"日志文件: {log_file}")
        logger.info(f"Python版本: {sys.version}")
        logger.info(f"操作系统: {platform.platform()}")
        logger.info(f"工作目录: {os.getcwd()}")

        return log_file

    except Exception as e:
        print(f"设置日志失败: {str(e)}")
        return None


class OrderWindow(QMainWindow):
    def __init__(self, cookies, account_name):
        try:
            super().__init__()
            logging.info(f"正在初始化订单窗口: {account_name}")

            self.setWindowTitle(f"订单查看 - {account_name}")
            # 调整窗口大小和位置
            screen = QApplication.primaryScreen().geometry()
            self.setGeometry(
                screen.width() // 4,  # 屏幕1/4位置
                screen.height() // 4,  # 屏幕1/4位置
                600,  # 减小宽度
                500,  # 减小高度
            )

            # 创建主窗口部件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            layout.setContentsMargins(0, 0, 0, 0)  # 移除边距

            # 创建WebView
            self.web_view = QWebEngineView()
            layout.addWidget(self.web_view)

            # 设置窗口样式
            self.setStyleSheet(
                """
                QMainWindow {
                    background-color: #f5f5f5;
                }
                QWebEngineView {
                    border: none;
                    background-color: white;
                    font-size: 10px;  /* 减小字体大小到10px */
                }
            """
            )

            # 设置 WebEngine 选项
            self.profile = QWebEngineProfile("jd_order_profile", self.web_view)
            self.profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
            )

            self.settings = self.profile.settings()
            self.settings.setAttribute(
                QWebEngineSettings.WebAttribute.WebGLEnabled, False
            )

            # 创建 QWebEnginePage 并设置给 web_view
            self.webpage = QWebEnginePage(self.profile, self.web_view)
            self.web_view.setPage(self.webpage)

            # 设置网页缩放比例
            self.web_view.setZoomFactor(0.7)  # 减小缩放比例到70%

            # 设置cookies（参照 test.py 方式）
            order_url = "https://trade.m.jd.com/order/orderlist_jdm.shtml?sceneval=2&jxsid=17389784862254908880&appCode=ms0ca95114&orderType=all&ptag=7155.1.11&source=m_inner_myJd.orderFloor_orderlist"
            domain = ".jd.com"
            cookie_str = '; '.join([f"{name}={value}" for name, value in cookies.items()])
            self.webpage.loadFinished.connect(lambda: self.webpage.runJavaScript(f"""
                document.cookie = '{cookie_str}';
                window.location.href = '{order_url}';
            """))

            # 设置窗口标志
            self.setWindowFlags(
                Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint
            )

            # 添加页面加载完成的处理
            self.web_view.loadFinished.connect(self.handle_load_finished)
            self.web_view.loadStarted.connect(self.handle_load_started)

            # 添加错误处理
            self.webpage.loadFinished.connect(self.handle_load_finished)
            self.webpage.loadStarted.connect(self.handle_load_started)

            logging.info("订单窗口初始化完成")

        except Exception as e:
            logging.error(f"订单窗口初始化失败: {str(e)}")
            logging.error(traceback.format_exc())
            raise

    def handle_load_started(self):
        logging.info("开始加载页面")

    def handle_load_finished(self, ok):
        if ok:
            logging.info("页面加载成功")
        else:
            logging.error("页面加载失败")


# 添加一个新的线程类来处理测试连接
class TestConnectionThread(QThread):
    success = Signal()  # 连接成功信号
    error = Signal(str)  # 连接失败信号

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            ql = Qinglong(self.config)
            ql.get_env()  # 测试连接
            self.success.emit()
        except Exception as e:
            self.error.emit(str(e))


class SettingsWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("青龙面板设置")
        self.setFixedSize(600, 400)  # 增加窗口大小

        # 创建主窗口部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)  # 增加间距
        layout.setContentsMargins(30, 30, 30, 30)  # 增加边距

        # 创建输入框和说明标签
        self.host_input = QLineEdit()
        self.host_input.setMinimumHeight(36)  # 设置最小高度
        self.host_input.setPlaceholderText("例如: http://localhost:5700")

        self.client_id_input = QLineEdit()
        self.client_id_input.setMinimumHeight(36)  # 设置最小高度
        self.client_id_input.setPlaceholderText("在青龙面板系统设置->应用设置中获取")

        self.client_secret_input = QLineEdit()
        self.client_secret_input.setMinimumHeight(36)
        self.client_secret_input.setPlaceholderText(
            "在青龙面板系统设置->应用设置中获取"
        )
        self.client_secret_input.setEchoMode(
            QLineEdit.EchoMode.Password
        )  # 设置为密码模式

        # 添加鼠标事件处理
        self.client_secret_input.installEventFilter(self)

        # 添加输入框和标签
        for label_text, input_widget, tip_text in [
            (
                "青龙面板地址:",
                self.host_input,
                "请输入青龙面板的完整地址，包含http://或https://",
            ),
            (
                "Client ID:",
                self.client_id_input,
                "在青龙面板的系统设置->应用设置中创建应用获取",
            ),
            (
                "Client Secret:",
                self.client_secret_input,
                "在青龙面板的系统设置->应用设置中创建应用获取",
            ),
        ]:
            group_layout = QVBoxLayout()
            group_layout.setSpacing(8)  # 设置组内间距

            # 添加标签
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold; font-size: 14px;")
            group_layout.addWidget(label)

            # 添加输入框
            group_layout.addWidget(input_widget)

            # 添加提示信息
            tip_label = QLabel(tip_text)
            tip_label.setStyleSheet("color: #666; font-size: 12px; padding-left: 2px;")
            group_layout.addWidget(tip_label)

            layout.addLayout(group_layout)

        # 添加按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)  # 设置按钮间距

        # 添加测试连接按钮
        self.test_btn = QPushButton("测试连接")
        self.test_btn.setMinimumHeight(36)
        self.test_btn.clicked.connect(self.test_connection)

        # 添加保存按钮
        self.save_btn = QPushButton("保存设置")
        self.save_btn.setMinimumHeight(36)  # 设置按钮高度
        self.save_btn.clicked.connect(self.save_settings)

        button_layout.addWidget(self.test_btn)
        button_layout.addWidget(self.save_btn)
        layout.addLayout(button_layout)

        # 加载现有设置
        self.load_settings()

        # 设置样式
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit[echoMode="2"] {  /* Password mode */
                lineedit-password-character: 9679;  /* 使用圆点字符 */
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #1890ff;
                border-width: 1.5px;
            }
            QPushButton {
                padding: 8px 20px;
                background-color: #1890ff;
                color: white;
                border: none;
                border-radius: 6px;
                min-width: 120px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
            QLabel {
                color: #333;
            }
        """
        )

        self.parent = parent  # 保存父窗口引用

    def eventFilter(self, obj, event):
        """事件过滤器，处理鼠标悬浮事件"""
        if obj == self.client_secret_input:
            if event.type() == event.Type.Enter:  # 鼠标进入
                self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Normal)
            elif event.type() == event.Type.Leave:  # 鼠标离开
                self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        return super().eventFilter(obj, event)

    def test_connection(self):
        config = {
            "host": self.host_input.text().strip(),
            "client_id": self.client_id_input.text().strip(),
            "client_secret": self.client_secret_input.text().strip(),
        }

        if not all(config.values()):
            QMessageBox.warning(self, "错误", "请填写所有必要信息！")
            return

        # 禁用按钮，显示加载状态
        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")
        self.save_btn.setEnabled(False)

        # 创建并启动测试线程
        self.test_thread = TestConnectionThread(config)
        self.test_thread.success.connect(self.on_test_success)
        self.test_thread.error.connect(self.on_test_error)
        self.test_thread.finished.connect(self.on_test_finished)
        self.test_thread.start()

    def on_test_success(self):
        # 在状态栏显示成功消息
        if isinstance(self.parent, AccountListWindow):
            self.parent.statusBar.showMessage("✅ 连接测试成功", 3000)
        else:
            # 如果没有父窗口的状态栏，则显示在当前窗口标题
            self.setWindowTitle("青龙面板设置 - 连接成功")
            # 3秒后恢复原标题
            QTimer.singleShot(3000, lambda: self.setWindowTitle("青龙面板设置"))

    def on_test_error(self, error_msg):
        QMessageBox.critical(self, "错误", f"连接青龙面板失败：{error_msg}")

    def on_test_finished(self):
        # 恢复按钮状态
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")
        self.save_btn.setEnabled(True)

    def load_settings(self):
        try:
            config_path = get_config_path()
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                    self.host_input.setText(config.get("host", ""))
                    self.client_id_input.setText(config.get("client_id", ""))
                    self.client_secret_input.setText(config.get("client_secret", ""))
        except Exception as e:
            print(f"加载配置失败: {str(e)}")

    def save_settings(self):
        config = {
            "host": self.host_input.text().strip(),
            "client_id": self.client_id_input.text().strip(),
            "client_secret": self.client_secret_input.text().strip(),
        }

        if not all(config.values()):
            QMessageBox.warning(self, "错误", "请填写所有必要信息！")
            return

        # 禁用按钮并显示保存状态
        self.test_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.save_btn.setText("保存中...")

        try:
            # 直接保存配置文件
            config_path = get_config_path()
            with open(config_path, "w") as f:
                json.dump(config, f)

            # 更新状态栏显示
            if isinstance(self.parent, AccountListWindow):
                self.parent.statusBar.showMessage("青龙配置已保存", 3000)
                # 只在设置窗口保存后自动同步一次
                QTimer.singleShot(100, lambda: self.parent.sync_from_qinglong(is_auto=False))

            # 关闭设置窗口
            self.close()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败：{str(e)}")
        finally:
            # 恢复按钮状态
            self.test_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            self.save_btn.setText("保存设置")

    def closeEvent(self, event):
        """重写关闭事件，在窗口关闭时通知父窗口"""
        if isinstance(self.parent, AccountListWindow):
            self.parent.check_qinglong_config()
        super().closeEvent(event)


class CheckCookieThread(QThread):
    result = Signal(int, str)  # row, status

    def __init__(self, row, cookie_data, parent=None):
        super().__init__(parent)
        self.row = row
        self.cookie_data = cookie_data

    def run(self):
        try:
            cookie_str = f"pt_key={self.cookie_data['pt_key']};pt_pin={self.cookie_data['pt_pin']};pt_st={self.cookie_data['pt_st']};"
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(need_login(cookie_str))
            loop.close()
            if result:
                self.result.emit(self.row, "❌ 失效")
            else:
                self.result.emit(self.row, "✅ 有效")
        except Exception as e:
            logging.error(f"检查cookie状态失败: {str(e)}")
            self.result.emit(self.row, "⚠️ 错误")


class BatchCheckThread(QThread):
    progress = Signal(int, str)  # row, status
    finished_signal = Signal(list)  # invalid_names

    def __init__(self, table_widget, parent=None):
        super().__init__(parent)
        self.table_widget = table_widget

    def run(self):
        try:
            row_count = self.table_widget.rowCount()
            cookies_list = []

            # 收集所有需要检测的cookie
            for row in range(row_count):
                item = self.table_widget.item(row, 1)
                if item:
                    data = item.data(Qt.ItemDataRole.UserRole)
                    if data:
                        cookies_list.append((row, data))

            invalid_names = []

            # 使用线程池进行并发检测
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                future_to_row = {}

                # 提交所有检测任务
                for row, data in cookies_list:
                    future = executor.submit(self.check_one_cookie, row, data)
                    future_to_row[future] = row

                # 处理结果
                for future in concurrent.futures.as_completed(future_to_row):
                    try:
                        row, status = future.result()
                        self.progress.emit(row, status)

                        # 收集失效的账号名
                        if status == "❌ 失效":
                            name_item = self.table_widget.item(row, 1)
                            if name_item:
                                invalid_names.append(name_item.text())
                    except Exception as e:
                        logging.error(f"批量检测失败: {str(e)}")

            # 发送完成信号
            self.finished_signal.emit(invalid_names)

        except Exception as e:
            logging.error(f"批量检测线程失败: {str(e)}")
            self.finished_signal.emit([])

    def check_one_cookie(self, row, data):
        """检测单个cookie"""
        try:
            cookie_str = f"pt_key={data['pt_key']};pt_pin={data['pt_pin']};pt_st={data['pt_st']};"
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(need_login(cookie_str))
            loop.close()
            return (row, "❌ 失效" if result else "✅ 有效")
        except Exception as e:
            return (row, "⚠️ 错误")


class AccountListWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JD账户管理器")
        self.setGeometry(100, 100, 600, 600)

        # 设置窗口图标
        icon_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "jd_new_logo.png"),
            os.path.join(os.getcwd(), "utils", "jd_new_logo.png"),
            "utils/jd_new_logo.png",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "jd.png"),
            os.path.join(os.getcwd(), "utils", "jd.png"),
            "utils/jd.png"
        ]

        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    self.setWindowIcon(QIcon(icon_path))
                    break
                except Exception:
                    continue

        # 创建主窗口部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 修改顶部按钮布局
        top_layout = QHBoxLayout()

        # 添加同步并检测按钮
        self.sync_btn = QPushButton("🔄 同步并检测")
        self.sync_btn.clicked.connect(self.sync_and_check)
        top_layout.addWidget(self.sync_btn)

        # 创建青龙菜单按钮
        self.ql_btn = QPushButton("🔮 青龙面板")
        self.ql_btn.setFixedWidth(120)
        self.ql_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #1890ff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
            QPushButton:disabled {
                background-color: #bae7ff;
                color: rgba(255, 255, 255, 0.8);
            }
            """
        )

        # 创建下拉菜单
        self.ql_menu = QMenu(self)
        self.ql_menu.setStyleSheet(
            """
            QMenu {
                background-color: white;
                border: 1px solid #e8e8e8;
                border-radius: 4px;
                padding: 4px 0;
                color: #333;  /* 设置菜单文字颜色 */
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
                margin: 2px 4px;
                color: #333;  /* 设置菜单项文字颜色 */
            }
            QMenu::item:selected {
                background-color: #e6f7ff;
                color: #1890ff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #f0f0f0;
                margin: 4px 0;
            }
            """
        )

        # 添加菜单项
        self.settings_action = self.ql_menu.addAction("⚙️ 面板设置")
        # self.sync_action = self.ql_menu.addAction("🔄 同步账号")  # 移除菜单里的同步账号

        # 设置按钮点击事件
        self.ql_btn.clicked.connect(self.show_ql_menu)
        self.settings_action.triggered.connect(self.show_settings)
        # self.sync_action.triggered.connect(lambda: self.sync_from_qinglong(is_auto=False))

        # 添加按钮到布局
        top_layout.addStretch()  # 添加弹簧将按钮推到右边
        top_layout.addWidget(self.ql_btn)

        main_layout.addLayout(top_layout)

        # 创建表格部件
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["序号", "账户", "添加时间", "状态"])
        self.table_widget.verticalHeader().setVisible(False)  # 隐藏默认的行号

        # 设置表格样式
        self.table_widget.setStyleSheet(
            """
            QTableWidget {
                background-color: white;
                alternate-background-color: #fafafa;
                border: 1px solid #ddd;
                border-radius: 4px;
                color: #333;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 8px;
                color: #333;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                color: #333;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ddd;
            }
            QTableWidget::item:selected {
                background-color: #e6f7ff;
                color: #1890ff;
            }
            /* 序号列的特殊样式 */
            QTableWidget::item:first-column {
                color: #666;
                font-size: 13px;
            }
            """
        )

        # 设置表格属性
        self.table_widget.setShowGrid(True)  # 显示网格线
        self.table_widget.setMouseTracking(True)

        # 设置行为为整行选择
        self.table_widget.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table_widget.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        # 设置表格列宽
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # 序号列固定宽度
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 账户列自适应
        header.setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )  # 时间列自适应内容
        header.setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )  # 状态列自适应内容
        self.table_widget.setColumnWidth(0, 50)  # 设置序号列宽度

        main_layout.addWidget(self.table_widget)

        # 连接右键菜单事件
        self.table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)

        # 设置样式表
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                font-size: 14px;
                gridline-color: #f0f0f0;
                selection-background-color: transparent;
            }
            QTableWidget::item {
                border: none;
                padding: 8px;
            }
            /* 设置整行悬浮效果 */
            QTableWidget::item:hover {
                background-color: #e6f7ff;
            }
            QHeaderView::section {
                background-color: #fafafa;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ddd;
                font-weight: bold;
            }
            QMenu {
                background-color: white;
                border: 1px solid #ddd;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #f5f5f5;
                color: #1890ff;
            }
        """
        )

        # 修改状态栏初始化
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # 添加加载指示器
        self.loading_label = QLabel()
        self.statusBar.addWidget(self.loading_label)

        self.statusBar.setStyleSheet(
            """
            QStatusBar {
                background-color: #fafafa;
                border-top: 1px solid #ddd;
                padding: 5px;
                font-size: 13px;
                color: #333;  /* 设置状态栏文字颜色 */
            }
            QLabel {
                padding: 3px;
                color: #333;  /* 设置状态栏标签文字颜色 */
            }
        """
        )

        # 保存检查线程的引用
        self.check_threads = []
        self.check_total = 0  # 总共要检测的数量
        self.check_finished = 0  # 已完成检测的数量
        # 初始检查青龙配置（并自动同步并检测）
        QTimer.singleShot(0, self.check_qinglong_config)
        QTimer.singleShot(0, self.sync_and_check)

    def parse_account_data(self, text):
        # 分割多行文本
        lines = text.strip().split("\n")
        accounts = []

        for line in lines:
            # 定义需要匹配的字段
            fields = {"pt_key": None, "pt_st": None, "pt_pin": None, "__time": None, "username": None}

            # 使用正则表达式匹配每个字段
            for key in fields.keys():
                pattern = f"{key}=([^;]+)"
                match = re.search(pattern, line)
                if match:
                    fields[key] = match.group(1)

            # 如果必要字段存在，添加到账户列表
            if fields["pt_key"] and fields["pt_pin"]:
                # pt_st 兼容老数据，如果没有则用 pt_key 值
                if not fields["pt_st"]:
                    fields["pt_st"] = fields["pt_key"]
                # 保存原始时间戳，不进行格式化
                if fields["__time"]:
                    try:
                        # 验证时间戳是否有效
                        timestamp = float(fields["__time"])
                        datetime.fromtimestamp(timestamp)  # 测试是否是有效的时间戳
                    except ValueError:
                        fields["__time"] = None

                accounts.append(fields)

        return accounts

    def show_context_menu(self, position):
        item = self.table_widget.itemAt(position)

        if item is None:
            # 在空白处右键时直接导入
            self.add_from_clipboard()
            return

        # 获取当前行的账户数据
        row = item.row()
        account_item = self.table_widget.item(row, 1)  # 获取账户列的item
        if not account_item:
            return

        # 选中整行
        self.table_widget.selectRow(row)

        # 显示右键菜单
        context_menu = QMenu(self)
        context_menu.setStyleSheet(
            """
            QMenu {
                background-color: white;
                border: 1px solid #ddd;
                padding: 5px;
                color: #333;  /* 设置右键菜单文字颜色 */
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
                color: #333;  /* 设置右键菜单项文字颜色 */
            }
            QMenu::item:selected {
                background-color: #f5f5f5;
                color: #1890ff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #eee;
                margin: 5px 15px;
            }
        """
        )

        check_status_action = context_menu.addAction("🍪 检查状态")
        delete_action = context_menu.addAction("🗑️ 删除账户")
        details_action = context_menu.addAction("📋 查看详情")
        orders_action = context_menu.addAction("🛒 查看订单")
        asset_action = context_menu.addAction("💰 账户资产")
        service_action = context_menu.addAction("🎯 京东客服")  # 新增客服选项
        auto_login_action = context_menu.addAction("🔐 自动登录")  # 新增自动登录选项

        context_menu.addSeparator()

        more_menu = context_menu.addMenu("⚙️ 更多操作")
        export_action = more_menu.addAction("📤 导出数据")
        backup_action = more_menu.addAction("备份账户")

        action = context_menu.exec(self.table_widget.mapToGlobal(position))

        if action == check_status_action:
            self.check_cookie_status(account_item)
        elif action == delete_action:
            self.delete_account(account_item)
        elif action == details_action:
            self.show_details(account_item)
        elif action == orders_action:
            self.show_orders(account_item)
        elif action == asset_action:
            self.show_assets(account_item)
        elif action == service_action:
            self.show_service(account_item)  # 新增客服处理
        elif action == auto_login_action:
            self.auto_login_account(account_item)  # 新增自动登录处理
        elif action == export_action:
            self.export_data(account_item)
        elif action == backup_action:
            self.backup_account(account_item)

    def show_ql_menu(self):
        """显示青龙菜单"""
        # 在按钮下方显示菜单
        pos = self.ql_btn.mapToGlobal(self.ql_btn.rect().bottomLeft())
        self.ql_menu.popup(pos)

    def check_qinglong_config(self):
        """检查青龙配置状态并更新同步按钮状态"""
        try:
            config_path = get_config_path()
            has_config = os.path.exists(config_path)
            if has_config:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    has_config = all(config.values())  # 确保所有配置项都有值

            # 更新同步按钮状态
            self.sync_btn.setEnabled(has_config)
            if not has_config:
                self.sync_btn.setText("🔄 同步账号 (请先配置青龙面板)")
            else:
                self.sync_btn.setText("🔄 同步账号")

        except Exception as e:
            self.sync_btn.setEnabled(False)
            self.sync_btn.setText("🔄 同步账号 (配置检查失败)")
            logging.error(f"检查青龙配置失败: {str(e)}")

    def show_settings(self):
        """显示设置窗口"""
        self.settings_window = SettingsWindow(self)
        self.settings_window.show()

    def add_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()

        # 解析数据
        accounts = self.parse_account_data(text)

        if not accounts:
            QMessageBox.warning(self, "错误", "剪切板数据格式不正确！")
            return

        # 记录添加结果
        success_count = 0
        update_count = 0
        failed_count = 0

        # 尝试同步到青龙（如果配置了的话）
        has_qinglong = False
        config = None
        try:
            config_path = get_config_path()
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                    has_qinglong = True
        except Exception as e:
            print(f"读取青龙配置失败: {str(e)}")

        for account_data in accounts:
            try:
                # 检查是否已存在相同的pt_pin
                existing_row = self.find_existing_account(account_data["pt_pin"])

                # 准备显示数据
                username = account_data["username"] or account_data["pt_pin"]

                # 使用__time字段，如果存在则格式化，否则为空
                if account_data.get("__time"):
                    try:
                        timestamp = float(account_data["__time"])
                        add_time = datetime.fromtimestamp(timestamp).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        add_time = ""
                else:
                    add_time = ""

                if existing_row >= 0:
                    # 更新现有账户
                    update_count += 1
                    self.update_table_row(
                        existing_row, username, add_time, account_data
                    )
                else:
                    # 新增账户
                    success_count += 1
                    self.add_table_row(username, add_time, account_data)

                # 如果配置了青龙，则同步到青龙
                if has_qinglong and config:
                    try:
                        env_data = {
                            "name": "JD_COOKIE",
                            "value": f"pt_key={account_data['pt_key']};pt_pin={account_data['pt_pin']};pt_st={account_data['pt_st']};",
                            "remarks": account_data.get("username", ""),
                        }
                        self.sync_thread = QinglongOperationThread(
                            "add_cookie", config, env_data
                        )
                        self.sync_thread.start()
                    except Exception as e:
                        print(f"同步到青龙失败: {str(e)}")

            except Exception as e:
                failed_count += 1
                print(f"添加账户失败: {str(e)}")

        # 显示结果
        result_message = []
        if success_count > 0:
            result_message.append(f"✅ 新增{success_count}个")
        if update_count > 0:
            result_message.append(f"🔄 更新{update_count}个")
        if failed_count > 0:
            result_message.append(f"❌ 失败{failed_count}个")

        if result_message:
            self.statusBar.showMessage(" | ".join(result_message), 3000)

    def add_table_row(self, username, add_time, account_data):
        row = self.table_widget.rowCount()
        self.table_widget.insertRow(row)

        # 添加序号
        num_item = QTableWidgetItem(str(row + 1))
        num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # 居中对齐
        num_item.setFlags(
            num_item.flags() & ~Qt.ItemFlag.ItemIsEditable
        )  # 设置为不可编辑
        self.table_widget.setItem(row, 0, num_item)

        # 添加账户名
        name_item = QTableWidgetItem(username)
        self.table_widget.setItem(row, 1, name_item)

        # 添加时间
        time_item = QTableWidgetItem(add_time)
        self.table_widget.setItem(row, 2, time_item)

        # 添加状态列
        status_item = QTableWidgetItem("")
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table_widget.setItem(row, 3, status_item)

        # 存储完整数据
        name_item.setData(Qt.ItemDataRole.UserRole, account_data)

    def update_table_row(self, row, username, add_time, account_data):
        # 序号保持不变

        # 更新账户名
        name_item = QTableWidgetItem(username)
        self.table_widget.setItem(row, 1, name_item)

        # 更新时间
        time_item = QTableWidgetItem(add_time)
        self.table_widget.setItem(row, 2, time_item)

        # 更新状态列（清空旧状态）
        status_item = QTableWidgetItem("")
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table_widget.setItem(row, 3, status_item)

        # 更新存储的数据
        name_item.setData(Qt.ItemDataRole.UserRole, account_data)

    def find_existing_account(self, pt_pin):
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, 1)  # 获取账户列的item
            data = item.data(Qt.ItemDataRole.UserRole)
            if data and data["pt_pin"] == pt_pin:
                return row
        return -1

    def update_row_numbers(self):
        """更新所有行的序号"""
        for row in range(self.table_widget.rowCount()):
            num_item = QTableWidgetItem(str(row + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # 居中对齐
            num_item.setFlags(
                num_item.flags() & ~Qt.ItemFlag.ItemIsEditable
            )  # 设置为不可编辑
            self.table_widget.setItem(row, 0, num_item)

    def delete_account(self, item):
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除账户 {item.text()} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.table_widget.removeRow(item.row())
            self.update_row_numbers()  # 删除后更新序号

    def show_details(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            details = f"账号详情:\n\n"
            details += f"用户名: {data['username'] or '未设置'}\n"
            details += f"PT_PIN: {data['pt_pin']}\n"
            details += f"PT_KEY: {data['pt_key']}\n"
            details += f"PT_ST: {data['pt_st']}\n"
            if data["__time"]:
                details += f"到期时间: {data['__time']}"

            QMessageBox.information(self, "账户详情", details)

    def show_orders(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            cookies = {"pt_key": data["pt_key"], "pt_st": data["pt_st"], "pt_pin": data["pt_pin"]}
            account_name = data["username"] or data["pt_pin"]
            self.order_window = OrderWindow(cookies, account_name)
            self.order_window.show()

    def show_assets(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            cookies = {"pt_key": data["pt_key"], "pt_st": data["pt_st"], "pt_pin": data["pt_pin"]}
            account_name = data["username"] or data["pt_pin"]
            self.asset_window = AssetWindow(cookies, account_name)
            self.asset_window.show()

    def export_data(self, item):
        QMessageBox.information(self, "导出数据", f"导出 {item.text()} 的数据")

    def backup_account(self, item):
        QMessageBox.information(self, "备份账户", f"备份 {item.text()} 的数据")

    def show_service(self, account_item):
        """显示京东客服"""
        try:
            account_data = account_item.data(Qt.ItemDataRole.UserRole)
            if not account_data:
                return

            cookies = {
                "pt_key": account_data["pt_key"],
                "pt_st": account_data["pt_st"],
                "pt_pin": account_data["pt_pin"],
            }

            self.service_window = ServiceWindow(cookies, account_item.text())
            self.service_window.show()

        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开客服失败：{str(e)}")

    def auto_login_account(self, account_item):
        """自动登录功能 - 打开登录页面让用户手动登录"""
        try:
            account_data = account_item.data(Qt.ItemDataRole.UserRole)
            if not account_data:
                QMessageBox.warning(self, "错误", "无法获取账户信息")
                return

            account_name = account_item.text()

            # 创建登录窗口
            self.login_window = JDLoginWindow(account_name, self)
            self.login_window.cookie_updated.connect(self.on_cookie_updated)
            self.login_window.show()

        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开登录页面失败：{str(e)}")

    def on_cookie_updated(self, account_name, new_cookie):
        """处理cookie更新"""
        try:
            # 更新本地表格数据
            for row in range(self.table_widget.rowCount()):
                item = self.table_widget.item(row, 1)
                if item and item.text() == account_name:
                    # 更新存储的数据
                    item.setData(Qt.ItemDataRole.UserRole, new_cookie)

                    # 更新状态
                    status_item = QTableWidgetItem("✅ 已更新")
                    status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table_widget.setItem(row, 3, status_item)

                    # 更新青龙面板
                    self.update_qinglong_cookie(account_name, new_cookie)
                    break

            QMessageBox.information(self, "成功", f"账户 {account_name} 的cookie已更新")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"更新cookie失败：{str(e)}")

    def update_qinglong_cookie(self, account_name, cookie_data):
        """更新青龙面板的cookie"""
        try:
            config_path = get_config_path()
            if not os.path.exists(config_path):
                QMessageBox.warning(self, "错误", "未找到青龙面板配置")
                return

            with open(config_path, "r") as f:
                config = json.load(f)

            # 构造cookie字符串
            cookie_str = f"pt_key={cookie_data['pt_key']};pt_pin={cookie_data['pt_pin']};pt_st={cookie_data['pt_st']};"

            # 准备环境变量数据
            env_data = {
                "name": "JD_COOKIE",
                "value": cookie_str,
                "remarks": account_name,
            }

            # 创建更新线程
            self.update_thread = QinglongOperationThread("add_cookie", config, env_data)
            self.update_thread.error.connect(self.on_update_error)
            self.update_thread.start()

        except Exception as e:
            QMessageBox.warning(self, "错误", f"更新青龙面板失败：{str(e)}")

    def on_update_error(self, error):
        """处理更新错误"""
        QMessageBox.warning(self, "错误", f"更新青龙面板失败：{error}")

    def import_from_qinglong(self):
        try:
            config_path = get_config_path()
            with open(config_path, "r") as f:
                config = json.load(f)

            # 创建并启动导入线程
            self.import_thread = QinglongOperationThread("import", config)
            self.import_thread.env_result.connect(self.process_imported_envs)
            self.import_thread.error.connect(self.on_import_error)
            self.import_thread.start()

        except Exception as e:
            QMessageBox.warning(self, "错误", f"读取配置失败：{str(e)}")

    def process_imported_envs(self, envs, after_sync_check=False):
        # 过滤出JD_COOKIE
        jd_cookies = [env for env in envs if env.get("name") == "JD_COOKIE"]

        if not jd_cookies:
            self.statusBar.showMessage("青龙面板中未找到JD_COOKIE", 3000)
            self.sync_btn.setEnabled(True)
            return

        success_count = 0
        update_count = 0
        failed_count = 0

        for env in jd_cookies:
            try:
                cookie = env["value"]
                remarks = env.get("remarks", "")

                # 构造完整的cookie字符串，包含remarks作为username
                full_cookie = cookie
                if remarks:
                    full_cookie += f";username={remarks.split('@')[0]}"

                # 使用parse_account_data处理cookie
                accounts = self.parse_account_data(full_cookie)
                if not accounts:
                    failed_count += 1
                    continue

                account_data = accounts[0]  # 获取解析后的账户数据

                # 检查是否已存在
                existing_row = self.find_existing_account(account_data["pt_pin"])

                # 使用优先级：username > pt_pin
                username = account_data["username"] or account_data["pt_pin"]

                # 使用cookie中的_time，如果没有则不显示时间
                add_time = ""
                if account_data.get("__time"):
                    try:
                        timestamp = float(account_data["__time"])
                        add_time = datetime.fromtimestamp(timestamp).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        pass
                else:
                    try:
                        # 2025-06-18T05:25:54.897Z --> 转东8区 2025-06-18 13:25:54
                        dt = datetime.strptime(env['updatedAt'], "%Y-%m-%dT%H:%M:%S.%fZ")
                        dt = dt.replace(tzinfo=timezone.utc)  # 明确为UTC时间
                        add_time = dt.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception as e:
                        add_time = ""

                if existing_row >= 0:
                    update_count += 1
                    self.update_table_row(
                        existing_row, username, add_time, account_data
                    )
                else:
                    success_count += 1
                    self.add_table_row(username, add_time, account_data)

            except Exception as e:
                failed_count += 1

        # 显示导入结果
        self.show_import_results(success_count, update_count, failed_count)
        self.loading_label.clear()
        if after_sync_check:
            QTimer.singleShot(100, self.batch_check_cookies_status)
        else:
            self.sync_btn.setEnabled(True)

    def on_import_error(self, error):
        QMessageBox.warning(self, "错误", f"从青龙导入失败：{error}")

    def show_import_results(self, success_count, update_count, failed_count):
        """显示导入结果"""
        self.loading_label.clear()

        result_message = []
        if success_count > 0:
            result_message.append(f"✅ 导入{success_count}个")
        if update_count > 0:
            result_message.append(f"🔄 更新{update_count}个")
        if failed_count > 0:
            result_message.append(f"❌ 失败{failed_count}个")

        if result_message:
            final_message = " | ".join(result_message)
        else:
            final_message = "没有需要同步的账号"

        self.statusBar.showMessage(final_message, 3000)

    def sync_and_check(self):
        """同步账号并批量异步检测cookie状态"""
        self.sync_btn.setEnabled(False)
        self.statusBar.showMessage("正在同步账号...", 0)
        self.loading_label.setText("🔄 正在同步青龙面板数据...")
        self.sync_from_qinglong(is_auto=False, after_sync_check=True)

    def sync_from_qinglong(self, is_auto=True, after_sync_check=False):
        """从青龙同步数据
        Args:
            is_auto (bool): 是否为自动同步
            after_sync_check (bool): 同步后是否批量检测cookie状态
        """
        try:
            config_path = get_config_path()
            if not os.path.exists(config_path):
                self.statusBar.showMessage("未检测到青龙配置，请先完成青龙设置", 5000)
                self.sync_btn.setEnabled(True)
                return
            with open(config_path, "r") as f:
                config = json.load(f)
            self.loading_label.setText("🔄 正在同步青龙面板数据...")
            self.statusBar.showMessage("正在连接青龙面板...", 0)
            self.import_thread = QinglongOperationThread("import", config)
            self.import_thread.env_result.connect(lambda envs: self.process_imported_envs(envs, after_sync_check))
            self.import_thread.error.connect(lambda error: self.on_sync_error(error, is_auto))
            self.import_thread.finished.connect(self.on_sync_finished)
            self.import_thread.start()
        except Exception as e:
            error_prefix = "自动同步" if is_auto else "同步"
            self.statusBar.showMessage(f"{error_prefix}失败：{str(e)}", 5000)
            self.loading_label.clear()
            self.sync_btn.setEnabled(True)

    def on_sync_error(self, error, is_auto=True):
        """同步错误处理"""
        error_prefix = "自动同步" if is_auto else "同步"
        self.statusBar.showMessage(f"{error_prefix}失败：{error}", 5000)
        self.loading_label.clear()

    def on_sync_finished(self):
        """同步完成处理"""
        self.loading_label.clear()

    def check_cookie_status(self, item):
        """检查单个cookie的状态"""
        row = item.row()
        account_data = self.table_widget.item(row, 1).data(Qt.ItemDataRole.UserRole)
        if not account_data:
            return

        status_item = QTableWidgetItem("检查中...")
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.setItem(row, 3, status_item)

        thread = CheckCookieThread(row, account_data, self)
        thread.result.connect(self.update_cookie_status)
        # 线程结束后自动从列表中移除，防止内存泄漏
        thread.finished.connect(lambda: self.check_threads.remove(thread))
        self.check_threads.append(thread)
        thread.start()

    def update_cookie_status(self, row, status):
        """更新表格中的cookie状态"""
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.setItem(row, 3, status_item)

    def batch_check_cookies_status(self):
        """批量异步检测所有cookie状态，检测完自动复制失效账号名"""
        self.statusBar.showMessage("正在批量检测cookie状态...", 0)
        self.loading_label.setText("🍪 正在检测cookie状态...")

        # 禁用同步按钮，防止重复操作
        self.sync_btn.setEnabled(False)

        # 创建批量检测线程
        self.batch_check_thread = BatchCheckThread(self.table_widget, self)
        self.batch_check_thread.progress.connect(self.update_cookie_status)
        self.batch_check_thread.finished_signal.connect(self.on_batch_check_finished)
        self.batch_check_thread.start()

    def on_batch_check_finished(self, invalid_names):
        """批量检测完成处理"""
        self.loading_label.clear()
        self.sync_btn.setEnabled(True)

        if invalid_names:
            # 将失效账号以逗号分隔复制到剪贴板
            QApplication.clipboard().setText(",".join(invalid_names))
            self.statusBar.showMessage(f"失效账号已复制到剪贴板 ({len(invalid_names)}个)", 3000)
        else:
            self.statusBar.showMessage("所有账号有效", 3000)


# 添加新的线程类用于保存设置和导入cookie
class QinglongOperationThread(QThread):
    success = Signal(str)  # 成功信号，携带成功消息
    error = Signal(str)   # 错误信号，携带错误消息
    import_result = Signal(list)  # 导入结果信号，携带账户数据列表
    env_result = Signal(list)  # 环境变量结果信号

    def __init__(self, operation, config, data=None):
        super().__init__()
        self.operation = operation  # 'save', 'import', 'add_cookie'
        self.config = config
        self.data = data

    def run(self):
        try:
            ql = Qinglong(self.config)

            if self.operation == "import":
                # 从青龙导入环境变量
                envs = ql.get_env()
                self.env_result.emit(envs)

            elif self.operation == "add_cookie":
                # 添加cookie到青龙
                ql.insert_env([self.data])
                # 不发送成功信号，避免弹窗

        except Exception as e:
            self.error.emit(str(e))


class AssetWindow(QMainWindow):
    def __init__(self, cookies, account_name):
        super().__init__()
        self.setWindowTitle(f"账户资产 - {account_name}")
        # 调整窗口大小和位置
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(
            screen.width() // 4,
            screen.height() // 4,
            400,  # 减小宽度
            600,  # 增加高度以适应内容
        )

        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建WebView
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        # 设置窗口样式
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWebEngineView {
                border: none;
                background-color: white;
                font-size: 14px;
            }
        """
        )

        # 创建自定义profile以管理cookie（改为使用defaultProfile，并设置User-Agent）
        import os
        os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.setHttpUserAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        self.webpage = QWebEnginePage(self.profile, self.web_view)
        self.web_view.setPage(self.webpage)

        # 设置网页缩放比例
        self.web_view.setZoomFactor(1.0)  # 调整缩放比例为1.0

        # JavaScript代码，用于调整页面样式
        js_code = """
        // 等待页面加载完成
        document.addEventListener('DOMContentLoaded', function() {
            // 添加自定义样式
            var style = document.createElement('style');
            style.textContent = `
                .asset-wrap {
                    width: 100% !important;
                    max-width: none !important;
                }
                .asset-content {
                    padding: 10px !important;
                }
                .asset-item {
                    margin-bottom: 10px !important;
                }
            `;
            document.head.appendChild(style);
        });
        """

        # 注入JavaScript代码
        self.webpage.loadFinished.connect(lambda: self.webpage.runJavaScript(js_code))

        # 设置cookies并加载页面
        asset_url = "https://my.m.jd.com/asset/index.html?sceneval=2&jxsid=17389784862254908880&appCode=ms0ca95114&ptag=7155.1.58"
        domain = ".jd.com"
        cookie_str = '; '.join([f"{name}={value}" for name, value in cookies.items()])
        self.webpage.loadFinished.connect(lambda: self.webpage.runJavaScript(f"""
            document.cookie = '{cookie_str}';
            window.location.href = '{asset_url}';
        """))

        # 添加页面加载完成的处理
        self.webpage.loadFinished.connect(self.handle_load_finished) # 连接加载完成信号

        # 移除置顶标志，只保留普通窗口标志
        self.setWindowFlags(Qt.WindowType.Window)

    def handle_load_finished(self, ok):
        if ok:
            logging.info("资产页面加载成功")
        else:
            logging.error("资产页面加载失败")


class ServiceWindow(QMainWindow):
    """京东客服窗口"""

    def __init__(self, cookies, account_name):
        super().__init__()
        self.setWindowTitle(f"京东客服 - {account_name}")

        # 调整窗口大小和位置
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(
            screen.width() // 4,
            screen.height() // 4,
            450,  # 设置合适的宽度
            700,  # 设置合适的高度
        )

        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建WebView
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        # 设置窗口样式
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWebEngineView {
                border: none;
                background-color: white;
            }
            """
        )

        # 创建自定义profile以管理cookie
        self.profile = QWebEngineProfile("jd_service_profile", self.web_view)
        self.webpage = QWebEnginePage(self.profile, self.web_view)
        self.web_view.setPage(self.webpage)

        # 设置网页缩放比例
        self.web_view.setZoomFactor(1.0)

        # 设置cookies并加载页面
        service_url = "https://jdcs.m.jd.com/after/index.action?categoryId=600&v=6&entry=m_self_jd&sid="
        domain = ".jd.com"
        cookie_str = '; '.join([f"{name}={value}" for name, value in cookies.items()])
        self.webpage.loadFinished.connect(lambda: self.webpage.runJavaScript(f"""
            document.cookie = '{cookie_str}';
            window.location.href = '{service_url}';
        """))

        # 添加页面加载完成的处理
        self.webpage.loadFinished.connect(self.handle_load_finished) # 连接加载完成信号

        # 移除置顶标志，只保留普通窗口标志
        self.setWindowFlags(Qt.WindowType.Window)

    def handle_load_finished(self, ok):
        if ok:
            logging.info("客服页面加载成功")
        else:
            logging.error("客服页面加载失败")


class PlaywrightLoginThread(QThread):
    """Playwright登录线程"""
    cookie_obtained = Signal(dict)  # cookie获取成功信号
    login_failed = Signal(str)  # 登录失败信号
    status_updated = Signal(str)  # 状态更新信号

    def __init__(self, account_name, parent=None, qinglong_config=None):
        super().__init__(parent)
        self.account_name = account_name
        self.qinglong_config = qinglong_config
        self.playwright_login = JDPlaywrightLogin()

    def run(self):
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 运行异步函数
            result = loop.run_until_complete(self.playwright_login.get_jd_cookies(
                self.account_name,
                self.qinglong_config
            ))
            loop.close()

            if result:
                self.cookie_obtained.emit(result)
            else:
                self.login_failed.emit("获取cookie失败")

        except Exception as e:
            self.login_failed.emit(f"Playwright登录失败: {str(e)}")


class JDLoginWindow(QMainWindow):
    """京东登录窗口"""

    cookie_updated = Signal(str, dict)  # account_name, cookie_data

    def __init__(self, account_name, parent=None):
        super().__init__(parent)
        self.account_name = account_name
        self.parent = parent
        self.setWindowTitle(f"京东登录 - {account_name}")

        # 调整窗口大小和位置
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(
            screen.width() // 4,
            screen.height() // 4,
            600,  # 减小宽度
            400,  # 减小高度
        )

        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # 设置窗口样式
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 14px;
                color: #333;
            }
            QPushButton {
                padding: 12px 24px;
                font-size: 14px;
                border-radius: 6px;
                border: none;
                background-color: #1890ff;
                color: white;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
            QPushButton:disabled {
                background-color: #d9d9d9;
                color: #999;
            }
            """
        )

        # 添加说明标签
        info_label = QLabel("🚀 Playwright 自动登录")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(info_label)

        desc_label = QLabel("点击下方按钮启动浏览器，扫码登录京东账号后自动获取cookie")
        desc_label.setStyleSheet("color: #666; margin-bottom: 20px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # 添加Playwright登录按钮
        self.playwright_btn = QPushButton("🚀 启动浏览器登录")
        self.playwright_btn.clicked.connect(self.get_cookies_with_playwright)
        layout.addWidget(self.playwright_btn)

        # 添加状态标签
        self.status_label = QLabel("准备就绪，点击按钮开始登录")
        self.status_label.setStyleSheet("color: #666; font-size: 12px; margin-top: 10px;")
        layout.addWidget(self.status_label)

        # 设置窗口标志
        self.setWindowFlags(Qt.WindowType.Window)

        # 初始化Playwright线程
        self.playwright_thread = None

    def get_cookies_with_playwright(self):
        """使用Playwright获取cookie"""
        if not PLAYWRIGHT_AVAILABLE:
            QMessageBox.warning(self, "错误", "Playwright模块未安装，请先安装playwright")
            return

        logging.info("开始使用Playwright获取cookie...")
        self.status_label.setText("正在启动浏览器...")
        self.playwright_btn.setEnabled(False)

        # 获取青龙配置
        qinglong_config = None
        try:
            config_path = get_config_path()
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    qinglong_config = json.load(f)
                    logging.info("已加载青龙面板配置")
            else:
                logging.warning("未找到青龙面板配置，将只获取cookie不保存")
        except Exception as e:
            logging.error(f"读取青龙配置失败: {str(e)}")

        # 创建并启动Playwright线程
        self.playwright_thread = PlaywrightLoginThread(
            self.account_name,
            self,
            qinglong_config
        )
        self.playwright_thread.cookie_obtained.connect(self.on_playwright_cookie_obtained)
        self.playwright_thread.login_failed.connect(self.on_playwright_login_failed)
        self.playwright_thread.status_updated.connect(self.status_label.setText)
        self.playwright_thread.start()

    def on_playwright_cookie_obtained(self, cookie_data):
        """Playwright获取到cookie的处理"""
        try:
            logging.info(f"Playwright获取到cookie: {cookie_data}")

            # 发送cookie更新信号
            # self.cookie_updated.emit(self.account_name, cookie_data)

            # 显示成功消息
            QMessageBox.information(self, "登录成功", f"账户 {self.account_name} 登录成功，cookie已更新")

            # 关闭窗口
            self.close()

        except Exception as e:
            logging.error(f"处理Playwright cookie失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"处理cookie失败: {str(e)}")
        finally:
            # 恢复按钮状态
            self.playwright_btn.setEnabled(True)

    def on_playwright_login_failed(self, error_msg):
        """Playwright登录失败的处理"""
        logging.error(f"Playwright登录失败: {error_msg}")
        QMessageBox.warning(self, "登录失败", f"Playwright登录失败: {error_msg}")
        self.status_label.setText("登录失败，请重试")
        self.playwright_btn.setEnabled(True)


def get_config_path():
    """获取配置文件路径"""
    # 获取用户家目录
    home = os.path.expanduser("~")
    # 创建应用配置目录
    app_dir = os.path.join(home, ".jd_manager")
    # 确保目录存在
    os.makedirs(app_dir, exist_ok=True)
    # 返回配置文件完整路径
    return os.path.join(app_dir, "config.json")


def main():
    try:
        # 启动优化：设置环境变量以减少Qt WebEngine的日志输出和启动时间
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-logging --disable-gpu-sandbox --disable-dev-shm-usage --no-sandbox --disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows --disable-ipc-flooding-protection"
        os.environ["QT_LOGGING_RULES"] = "qt.webenginecontext.debug=false;qt.webengine.*=false"
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        os.environ["QT_SCALE_FACTOR"] = "1"
        os.environ["QT_WEBENGINE_DISABLE_SANDBOX"] = "1"

        # 禁用不必要的Qt功能以加快启动
        os.environ["QT_DISABLE_GLIB"] = "1"
        os.environ["QT_DISABLE_ACCESSIBILITY"] = "1"

        # 设置日志
        log_file = setup_logging()
        logger = logging.getLogger("JDManager")

        if not log_file:
            print("警告: 日志系统初始化失败")

        logger.info("应用程序启动")

        app = QApplication(sys.argv)
        app.setApplicationName("JD Account Manager")

        # 设置应用图标 - 尝试多个可能的路径
        icon_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "jd_new_logo.png"),
            os.path.join(os.getcwd(), "utils", "jd_new_logo.png"),
            "utils/jd_new_logo.png",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "jd.png"),
            os.path.join(os.getcwd(), "utils", "jd.png"),
            "utils/jd.png"
        ]

        icon_set = False
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    app.setWindowIcon(QIcon(icon_path))
                    logger.info(f"已设置应用图标: {icon_path}")
                    icon_set = True
                    break
                except Exception as e:
                    logger.warning(f"设置图标失败 {icon_path}: {str(e)}")

        if not icon_set:
            logger.warning("未找到应用图标文件")

        # 捕获未处理的异常
        sys.excepthook = handle_exception

        window = AccountListWindow()
        window.show()

        if log_file:
            logger.info(f"日志文件位置: {log_file}")

        sys.exit(app.exec())

    except Exception as e:
        if log_file:
            logger.error(f"程序启动失败: {str(e)}")
            logger.error(traceback.format_exc())
        raise


def handle_exception(exc_type, exc_value, exc_traceback):
    """处理未捕获的异常"""
    logging.error("未捕获的异常:", exc_info=(exc_type, exc_value, exc_traceback))


if __name__ == "__main__":
    main()
