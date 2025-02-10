import json
import logging
import os
import platform
import re
import sys
import traceback
from datetime import datetime

from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
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

            # 创建自定义profile以管理cookie
            self.profile = QWebEngineProfile("jd_profile", self.web_view)
            self.webpage = QWebEnginePage(self.profile, self.web_view)
            self.web_view.setPage(self.webpage)

            # 设置网页缩放比例
            self.web_view.setZoomFactor(0.7)  # 减小缩放比例到70%

            # 设置cookies
            cookie_store = self.profile.cookieStore()
            for name, value in cookies.items():
                cookie_store.setCookie(self.create_cookie(name, value))

            # 加载京东订单页面
            self.web_view.setUrl(
                QUrl(
                    "https://trade.m.jd.com/order/orderlist_jdm.shtml?sceneval=2&jxsid=17389784862254908880&appCode=ms0ca95114&orderType=all&ptag=7155.1.11&source=m_inner_myJd.orderFloor_orderlist"
                )
            )

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

    def create_cookie(self, name, value):
        try:
            from PyQt6.QtNetwork import QNetworkCookie

            logging.info(f"创建Cookie: {name}")
            cookie = QNetworkCookie(name.encode(), value.encode())
            cookie.setDomain(".jd.com")
            cookie.setPath("/")
            return cookie
        except Exception as e:
            logging.error(f"创建Cookie失败: {str(e)}")
            logging.error(traceback.format_exc())
            raise


# 添加一个新的线程类来处理测试连接
class TestConnectionThread(QThread):
    success = pyqtSignal()  # 连接成功信号
    error = pyqtSignal(str)  # 连接失败信号

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
        self.client_secret_input.setMinimumHeight(36)  # 设置最小高度
        self.client_secret_input.setPlaceholderText(
            "在青龙面板系统设置->应用设置中获取"
        )

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
                # 异步导入现有的JD_COOKIE
                QTimer.singleShot(100, lambda: self.parent.import_from_qinglong())

            # 关闭设置窗口
            self.close()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败：{str(e)}")
        finally:
            # 恢复按钮状态
            self.test_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            self.save_btn.setText("保存设置")


class AccountListWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JD账户管理器")
        self.setGeometry(100, 100, 600, 600)

        # 创建主窗口部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 添加顶部按钮布局
        top_layout = QHBoxLayout()

        # 添加青龙设置按钮
        settings_btn = QPushButton("⚙️ 青龙设置")
        settings_btn.setFixedWidth(120)
        settings_btn.setStyleSheet(
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
        """
        )
        settings_btn.clicked.connect(self.show_settings)
        top_layout.addWidget(settings_btn, alignment=Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(top_layout)

        # 创建表格部件
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(3)
        self.table_widget.setHorizontalHeaderLabels(["序号", "账户", "添加时间"])
        self.table_widget.verticalHeader().setVisible(False)

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
            }
            QLabel {
                padding: 3px;
            }
        """
        )

        # 在初始化完成后，尝试自动同步
        QTimer.singleShot(500, self.auto_sync_from_qinglong)

    def parse_account_data(self, text):
        # 分割多行文本
        lines = text.strip().split("\n")
        accounts = []

        for line in lines:
            # 定义需要匹配的字段
            fields = {"pt_key": None, "pt_pin": None, "__time": None, "username": None}

            # 使用正则表达式匹配每个字段
            for key in fields.keys():
                pattern = f"{key}=([^;]+)"
                match = re.search(pattern, line)
                if match:
                    fields[key] = match.group(1)

            # 如果必要字段存在，添加到账户列表
            if fields["pt_key"] and fields["pt_pin"]:
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
            QMenu::separator {
                height: 1px;
                background-color: #eee;
                margin: 5px 15px;
            }
        """
        )

        edit_action = context_menu.addAction("✏️ 编辑账户")
        delete_action = context_menu.addAction("🗑️ 删除账户")
        details_action = context_menu.addAction("📋 查看详情")
        orders_action = context_menu.addAction("🛒 查看订单")
        asset_action = context_menu.addAction("💰 账户资产")

        context_menu.addSeparator()

        more_menu = context_menu.addMenu("⚙️ 更多操作")
        export_action = more_menu.addAction("📤 导出数据")
        backup_action = more_menu.addAction("备份账户")

        action = context_menu.exec(self.table_widget.mapToGlobal(position))

        if action == edit_action:
            self.edit_account(account_item)
        elif action == delete_action:
            self.delete_account(account_item)
        elif action == details_action:
            self.show_details(account_item)
        elif action == orders_action:
            self.show_orders(account_item)
        elif action == asset_action:
            self.show_assets(account_item)
        elif action == export_action:
            self.export_data(account_item)
        elif action == backup_action:
            self.backup_account(account_item)

    def show_settings(self):
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
                            "value": f"pt_key={account_data['pt_key']};pt_pin={account_data['pt_pin']};",
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
        num_item.setBackground(Qt.GlobalColor.transparent)  # 设置初始背景色
        self.table_widget.setItem(row, 0, num_item)

        # 添加账户名
        name_item = QTableWidgetItem(username)
        name_item.setBackground(Qt.GlobalColor.transparent)  # 设置初始背景色
        self.table_widget.setItem(row, 1, name_item)

        # 添加时间
        time_item = QTableWidgetItem(add_time)
        time_item.setBackground(Qt.GlobalColor.transparent)  # 设置初始背景色
        self.table_widget.setItem(row, 2, time_item)

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

        # 更新存储的数据
        name_item.setData(Qt.ItemDataRole.UserRole, account_data)

    def find_existing_account(self, pt_pin):
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, 1)  # 获取账户列的item
            data = item.data(Qt.ItemDataRole.UserRole)
            if data and data["pt_pin"] == pt_pin:
                return row
        return -1

    # 添加更新序号的方法
    def update_row_numbers(self):
        for row in range(self.table_widget.rowCount()):
            num_item = QTableWidgetItem(str(row + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_widget.setItem(row, 0, num_item)

    def edit_account(self, item):
        QMessageBox.information(self, "编辑账户", f"正在编辑: {item.text()}")

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
            if data["__time"]:
                details += f"到期时间: {data['__time']}"

            QMessageBox.information(self, "账户详情", details)

    def show_orders(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            cookies = {"pt_key": data["pt_key"], "pt_pin": data["pt_pin"]}
            account_name = data["username"] or data["pt_pin"]
            self.order_window = OrderWindow(cookies, account_name)
            self.order_window.show()

    def show_assets(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            cookies = {"pt_key": data["pt_key"], "pt_pin": data["pt_pin"]}
            account_name = data["username"] or data["pt_pin"]
            self.asset_window = AssetWindow(cookies, account_name)
            self.asset_window.show()

    def export_data(self, item):
        QMessageBox.information(self, "导出数据", f"导出 {item.text()} 的数据")

    def backup_account(self, item):
        QMessageBox.information(self, "备份账户", f"备份 {item.text()} 的数据")

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

    def process_imported_envs(self, envs):
        # 过滤出JD_COOKIE
        jd_cookies = [env for env in envs if env.get("name") == "JD_COOKIE"]

        if not jd_cookies:
            self.statusBar.showMessage("青龙面板中未找到JD_COOKIE", 3000)
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
                    full_cookie += f";username={remarks}"

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
                print(f"导入账户失败: {str(e)}")

        # 显示导入结果
        self.show_import_results(success_count, update_count, failed_count)

    def on_import_error(self, error):
        QMessageBox.warning(self, "错误", f"从青龙导入失败：{error}")

    def show_import_results(self, success_count, update_count, failed_count):
        result_message = []
        if success_count > 0:
            result_message.append(f"✅ 导入{success_count}个")
        if update_count > 0:
            result_message.append(f"🔄 更新{update_count}个")
        if failed_count > 0:
            result_message.append(f"❌ 失败{failed_count}个")

        if result_message:
            self.statusBar.showMessage(" | ".join(result_message), 3000)

    def auto_sync_from_qinglong(self):
        """自动从青龙同步数据"""
        try:
            # 检查配置文件是否存在
            config_path = get_config_path()
            if not os.path.exists(config_path):
                self.statusBar.showMessage("未检测到青龙配置，请先完成青龙设置", 5000)
                return

            with open(config_path, "r") as f:
                config = json.load(f)

            # 显示同步开始状态
            self.loading_label.setText("🔄 正在同步青龙面板数据...")
            self.statusBar.showMessage("正在连接青龙面板...", 0)  # 0表示不自动消失

            # 创建并启动导入线程
            self.import_thread = QinglongOperationThread("import", config)
            self.import_thread.env_result.connect(self.process_imported_envs)
            self.import_thread.error.connect(self.on_auto_sync_error)
            self.import_thread.finished.connect(self.on_auto_sync_finished)
            self.import_thread.start()

        except Exception as e:
            self.statusBar.showMessage(f"自动同步失败：{str(e)}", 5000)
            self.loading_label.clear()

    def on_auto_sync_error(self, error):
        """自动同步错误处理"""
        self.statusBar.showMessage(f"自动同步失败：{error}", 5000)
        self.loading_label.clear()

    def on_auto_sync_finished(self):
        """自动同步完成处理"""
        self.loading_label.clear()

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
            final_message = "自动同步完成: " + " | ".join(result_message)
            self.statusBar.showMessage(final_message, 5000)
        else:
            self.statusBar.showMessage("没有需要同步的账号", 5000)


# 添加新的线程类用于保存设置和导入cookie
class QinglongOperationThread(QThread):
    success = pyqtSignal(str)  # 成功信号，携带成功消息
    error = pyqtSignal(str)  # 错误信号，携带错误消息
    import_result = pyqtSignal(list)  # 导入结果信号，携带账户数据列表
    env_result = pyqtSignal(list)  # 环境变量结果信号

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

        # 创建自定义profile以管理cookie
        self.profile = QWebEngineProfile("jd_asset_profile", self.web_view)
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

        # 设置cookies
        cookie_store = self.profile.cookieStore()
        for name, value in cookies.items():
            cookie_store.setCookie(self.create_cookie(name, value))

        # 加载京东资产页面
        self.web_view.setUrl(
            QUrl(
                "https://my.m.jd.com/asset/index.html?sceneval=2&jxsid=17389784862254908880&appCode=ms0ca95114&ptag=7155.1.58"
            )
        )

        # 设置窗口标志
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)

    def create_cookie(self, name, value):
        from PyQt6.QtNetwork import QNetworkCookie

        cookie = QNetworkCookie(name.encode(), value.encode())
        cookie.setDomain(".jd.com")
        cookie.setPath("/")
        return cookie


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
        # 设置日志
        log_file = setup_logging()
        logger = logging.getLogger("JDManager")

        if not log_file:
            print("警告: 日志系统初始化失败")

        logger.info("应用程序启动")

        app = QApplication(sys.argv)
        app.setApplicationName("JD Account Manager")

        # 设置应用图标
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "utils", "jd.png"
        )
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            logger.info(f"已设置应用图标: {icon_path}")

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
