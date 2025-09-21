# tray_app.py
import sys
import aiohttp
import asyncio
import winsound
import os
from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QWidget,
                             QVBoxLayout, QLabel, QPushButton, QComboBox,
                             QSpinBox, QHBoxLayout, QMessageBox, QStyle)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, QTimer, QSize
from win10toast import ToastNotifier
import json

class PomodoroTrayApp(QWidget):
    def __init__(self):
        super().__init__()
        self.api_base = "http://localhost:8000/api"
        self.tasks = []
        self.current_task_id = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.toaster = ToastNotifier()

        self.init_ui()
        self.init_tray()
        asyncio.create_task(self.load_data())

    def init_ui(self):
        self.setWindowTitle("Pomodoro Tracker")
        self.setFixedSize(300, 400)

        layout = QVBoxLayout()

        # Timer display
        self.timer_label = QLabel("25:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.timer_label)

        # Mode label
        self.mode_label = QLabel("Work Time")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.mode_label)

        # Current task
        self.task_label = QLabel("No task selected")
        self.task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.task_label)

        # Controls
        controls_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_timer)
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_timer)
        self.pause_btn.setEnabled(False)
        self.skip_btn = QPushButton("Skip")
        self.skip_btn.clicked.connect(self.skip_timer)

        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.skip_btn)
        layout.addLayout(controls_layout)

        # Task selection
        layout.addWidget(QLabel("Select Task:"))
        self.task_combo = QComboBox()
        self.task_combo.currentIndexChanged.connect(self.task_changed)
        layout.addWidget(self.task_combo)

        # Settings
        settings_layout = QVBoxLayout()
        settings_layout.addWidget(QLabel("Work Duration (min):"))
        self.work_duration = QSpinBox()
        self.work_duration.setRange(1, 60)
        self.work_duration.setValue(25)
        self.work_duration.valueChanged.connect(self.settings_changed)
        settings_layout.addWidget(self.work_duration)

        settings_layout.addWidget(QLabel("Break Duration (min):"))
        self.break_duration = QSpinBox()
        self.break_duration.setRange(1, 30)
        self.break_duration.setValue(5)
        self.break_duration.valueChanged.connect(self.settings_changed)
        settings_layout.addWidget(self.break_duration)

        layout.addLayout(settings_layout)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh Tasks")
        self.refresh_btn.clicked.connect(lambda: asyncio.create_task(self.load_data()))
        layout.addWidget(self.refresh_btn)

        self.setLayout(layout)

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

        # Create tray menu
        tray_menu = QMenu()

        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()

    def quit_app(self):
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    async def api_request(self, endpoint, method="GET", data=None):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    f"{self.api_base}{endpoint}",
                    json=data
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"API error: {response.status}")
                        return None
        except Exception as e:
            print(f"Request error: {e}")
            return None

    async def load_data(self):
        # Load tasks
        tasks = await self.api_request("/tasks/")
        if tasks:
            self.tasks = tasks
            self.task_combo.clear()
            self.task_combo.addItem("No task", None)
            for task in tasks:
                self.task_combo.addItem(task["name"], task["id"])

        # Load timer state
        state = await self.api_request("/timer/")
        if state:
            self.update_ui_from_state(state)

    def update_ui_from_state(self, state):
        # Update timer display
        minutes = state["time_left"] // 60
        seconds = state["time_left"] % 60
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

        # Update mode
        mode = "Work Time" if state["is_work_time"] else "Break Time"
        self.mode_label.setText(mode)

        # Update buttons
        self.start_btn.setEnabled(not state["is_running"])
        self.pause_btn.setEnabled(state["is_running"])

        # Update current task
        if state["current_task_id"]:
            task = next((t for t in self.tasks if t["id"] == state["current_task_id"]), None)
            if task:
                self.task_label.setText(task["name"])
                # Select in combo box
                index = self.task_combo.findData(state["current_task_id"])
                if index >= 0:
                    self.task_combo.setCurrentIndex(index)

    async def update_timer_state(self):
        state = await self.api_request("/timer/")
        if state:
            self.update_ui_from_state(state)

    def update_timer(self):
        asyncio.create_task(self.update_timer_state())

    async def start_timer(self):
        await self.api_request("/timer/start/", "POST")
        self.timer.start(1000)  # Update every second

    async def pause_timer(self):
        await self.api_request("/timer/pause/", "POST")
        self.timer.stop()

    async def skip_timer(self):
        await self.api_request("/timer/skip/", "POST")
        await self.update_timer_state()

    async def settings_changed(self):
        work_mins = self.work_duration.value()
        break_mins = self.break_duration.value()
        await self.api_request(
            "/timer/settings/",
            "PUT",
            {"work_duration": work_mins, "break_duration": break_mins}
        )

    async def task_changed(self, index):
        task_id = self.task_combo.itemData(index)
        if task_id:
            await self.api_request(f"/timer/task/{task_id}", "PUT")
            # Update task label
            task = next((t for t in self.tasks if t["id"] == task_id), None)
            if task:
                self.task_label.setText(task["name"])

    def show_notification(self, title, message, is_work_complete=False):
        # Show system notification
        self.toaster.show_toast(
            title,
            message,
            duration=10,
            threaded=True
        )

        # Play sound
        if is_work_complete:
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
        else:
            winsound.PlaySound("SystemQuestion", winsound.SND_ALIAS)

        # Flash taskbar icon
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

async def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    tray_app = PomodoroTrayApp()
    tray_app.show()

    # Start WebSocket connection for real-time updates
    asyncio.create_task(tray_app.websocket_listener())

    # Run the application
    await asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    asyncio.run(main())