# desktop_app.py
import asyncio
import aiohttp
import json
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import winsound
import os
from datetime import datetime, timedelta
from pystray import MenuItem as item, Icon as icon
from PIL import Image, ImageDraw
import sys

class PomodoroDesktopApp:
    def __init__(self):
        self.api_base = "http://localhost:8000/api"
        self.session = None
        self.tasks = []
        self.current_task_id = None
        self.timer_state = {
            "is_running": False,
            "is_work_time": True,
            "time_left": 1500,  # 25 minutes in seconds
            "work_duration": 1500,
            "break_duration": 300,
            "current_task_id": None
        }
        self.root = None
        self.tray_icon = None
        self.is_running = True
        
        # Настройки звуков
        self.sound_enabled = True
        self.work_sound = "work_complete.wav"
        self.break_sound = "break_complete.wav"
        
        # Создаем звуковые файлы если их нет
        self.create_sound_files()

    def create_sound_files(self):
        """Создает простые звуковые файлы для уведомлений"""
        try:
            # Создаем простой звук для завершения работы (более высокий тон)
            if not os.path.exists(self.work_sound):
                # Генерируем простой звук с помощью winsound
                # Это будет системный звук Windows
                pass
            
            # Создаем простой звук для завершения перерыва (более низкий тон)
            if not os.path.exists(self.break_sound):
                pass
        except Exception as e:
            print(f"Ошибка создания звуковых файлов: {e}")

    async def init_session(self):
        """Инициализация HTTP сессии"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        """Закрытие HTTP сессии"""
        if self.session:
            await self.session.close()

    async def api_request(self, endpoint, method="GET", data=None):
        """Выполнение HTTP запроса к API"""
        try:
            await self.init_session()
            url = f"{self.api_base}{endpoint}"
            
            if method == "GET":
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"API error: {response.status}")
                        return None
            elif method == "POST":
                async with self.session.post(url, json=data) as response:
                    if response.status in [200, 201]:
                        return await response.json()
                    else:
                        print(f"API error: {response.status}")
                        return None
            elif method == "PUT":
                async with self.session.put(url, json=data) as response:
                    if response.status in [200, 204]:
                        return await response.json() if response.status == 200 else {"success": True}
                    else:
                        print(f"API error: {response.status}")
                        return None
            elif method == "DELETE":
                async with self.session.delete(url) as response:
                    if response.status in [200, 204]:
                        return {"success": True}
                    else:
                        print(f"API error: {response.status}")
                        return None
        except aiohttp.ClientConnectorError:
            print("Не удается подключиться к серверу. Убедитесь, что сервер запущен на localhost:8000")
            return None
        except Exception as e:
            print(f"API request failed: {e}")
            return None

    async def load_tasks(self):
        """Загрузка задач с сервера"""
        try:
            tasks_data = await self.api_request("/tasks/")
            if tasks_data:
                self.tasks = tasks_data
                return True
        except Exception as e:
            print(f"Failed to load tasks: {e}")
        return False

    async def load_timer_state(self):
        """Загрузка состояния таймера с сервера"""
        try:
            state = await self.api_request("/timer/")
            if state:
                self.timer_state.update(state)
                return True
        except Exception as e:
            print(f"Failed to load timer state: {e}")
        return False

    async def start_timer(self):
        """Запуск таймера"""
        await self.api_request("/timer/start/", "POST")

    async def pause_timer(self):
        """Пауза таймера"""
        await self.api_request("/timer/pause/", "POST")

    async def skip_timer(self):
        """Пропуск таймера"""
        await self.api_request("/timer/skip/", "POST")

    async def set_current_task(self, task_id):
        """Установка текущей задачи"""
        await self.api_request(f"/timer/task/{task_id}", "PUT")

    async def add_pomodoro(self, task_id, duration=25):
        """Добавление выполненного помидора"""
        await self.api_request("/pomodoros/", "POST", {
            "task_id": task_id,
            "duration": duration
        })

    def play_sound(self, sound_type="work"):
        """Воспроизведение звука"""
        if not self.sound_enabled:
            return
            
        try:
            if sound_type == "work":
                # Звук завершения работы - более высокий тон
                winsound.Beep(1000, 500)  # 1000 Hz, 500 ms
            else:
                # Звук завершения перерыва - более низкий тон
                winsound.Beep(600, 500)   # 600 Hz, 500 ms
        except Exception as e:
            print(f"Ошибка воспроизведения звука: {e}")

    def show_notification(self, title, message, sound_type="work"):
        """Показ уведомления"""
        try:
            # Показываем системное уведомление
            messagebox.showinfo(title, message)
            
            # Воспроизводим звук
            self.play_sound(sound_type)
            
            # Если приложение свернуто, мигаем в трее
            if self.tray_icon:
                self.tray_icon.notify(message, title)
        except Exception as e:
            print(f"Ошибка показа уведомления: {e}")

    def create_tray_icon(self):
        """Создание иконки в системном трее"""
        # Создаем простое изображение для иконки
        image = Image.new('RGB', (64, 64), color='red')
        draw = ImageDraw.Draw(image)
        draw.ellipse([16, 16, 48, 48], fill='red', outline='darkred', width=2)
        
        # Создаем меню трея
        menu = (
            item('Показать', self.show_main_window),
            item('Скрыть', self.hide_main_window),
            item('Настройки', self.show_settings),
            item('Выход', self.quit_app)
        )
        
        self.tray_icon = icon("Pomodoro", image, "Pomodoro Timer", menu)
        return self.tray_icon

    def show_main_window(self, icon=None, item=None):
        """Показать главное окно"""
        if self.root:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

    def hide_main_window(self, icon=None, item=None):
        """Скрыть главное окно"""
        if self.root:
            self.root.withdraw()

    def show_settings(self, icon=None, item=None):
        """Показать настройки"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Настройки")
        settings_window.geometry("300x200")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Звуки
        sound_var = tk.BooleanVar(value=self.sound_enabled)
        sound_check = ttk.Checkbutton(settings_window, text="Включить звуки", variable=sound_var)
        sound_check.pack(pady=10)
        
        def save_settings():
            self.sound_enabled = sound_var.get()
            settings_window.destroy()
        
        ttk.Button(settings_window, text="Сохранить", command=save_settings).pack(pady=10)

    def quit_app(self, icon=None, item=None):
        """Выход из приложения"""
        self.is_running = False
        if self.tray_icon:
            self.tray_icon.stop()
        if self.root:
            self.root.quit()
        sys.exit(0)

    def create_main_window(self):
        """Создание главного окна"""
        self.root = tk.Tk()
        self.root.title("Pomodoro Timer")
        self.root.geometry("400x600")
        self.root.protocol("WM_DELETE_WINDOW", self.hide_main_window)
        
        # Стиль
        style = ttk.Style()
        style.theme_use('clam')
        
        # Главный фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Таймер
        timer_frame = ttk.LabelFrame(main_frame, text="Таймер", padding="10")
        timer_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.timer_label = ttk.Label(timer_frame, text="25:00", font=("Arial", 24, "bold"))
        self.timer_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        self.mode_label = ttk.Label(timer_frame, text="Готов к работе", font=("Arial", 12))
        self.mode_label.grid(row=1, column=0, columnspan=2, pady=5)
        
        self.task_label = ttk.Label(timer_frame, text="Выберите задачу", font=("Arial", 10))
        self.task_label.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Кнопки управления
        button_frame = ttk.Frame(timer_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="Старт", command=self.start_timer_click)
        self.start_btn.grid(row=0, column=0, padx=5)
        
        self.pause_btn = ttk.Button(button_frame, text="Пауза", command=self.pause_timer_click, state="disabled")
        self.pause_btn.grid(row=0, column=1, padx=5)
        
        self.skip_btn = ttk.Button(button_frame, text="Пропустить", command=self.skip_timer_click)
        self.skip_btn.grid(row=0, column=2, padx=5)
        
        # Настройки таймера
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки", padding="10")
        settings_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(settings_frame, text="Работа (мин):").grid(row=0, column=0, sticky=tk.W)
        self.work_duration = tk.StringVar(value="25")
        work_spin = ttk.Spinbox(settings_frame, from_=1, to=60, textvariable=self.work_duration, width=10)
        work_spin.grid(row=0, column=1, sticky=tk.E, padx=(5, 0))
        
        ttk.Label(settings_frame, text="Перерыв (мин):").grid(row=1, column=0, sticky=tk.W)
        self.break_duration = tk.StringVar(value="5")
        break_spin = ttk.Spinbox(settings_frame, from_=1, to=30, textvariable=self.break_duration, width=10)
        break_spin.grid(row=1, column=1, sticky=tk.E, padx=(5, 0))
        
        # Задачи
        tasks_frame = ttk.LabelFrame(main_frame, text="Задачи", padding="10")
        tasks_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Список задач
        self.tasks_listbox = tk.Listbox(tasks_frame, height=8)
        self.tasks_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Скроллбар для списка задач
        scrollbar = ttk.Scrollbar(tasks_frame, orient="vertical", command=self.tasks_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tasks_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Кнопки для задач
        task_buttons_frame = ttk.Frame(tasks_frame)
        task_buttons_frame.grid(row=1, column=0, columnspan=2, pady=(5, 0))
        
        ttk.Button(task_buttons_frame, text="Выбрать", command=self.select_task).grid(row=0, column=0, padx=2)
        ttk.Button(task_buttons_frame, text="+ Помидор", command=self.add_pomodoro_click).grid(row=0, column=1, padx=2)
        ttk.Button(task_buttons_frame, text="Обновить", command=self.refresh_tasks).grid(row=0, column=2, padx=2)
        
        # Настройка весов для растягивания
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        tasks_frame.columnconfigure(0, weight=1)
        tasks_frame.rowconfigure(0, weight=1)

    def update_timer_display(self):
        """Обновление отображения таймера"""
        minutes = self.timer_state["time_left"] // 60
        seconds = self.timer_state["time_left"] % 60
        self.timer_label.config(text=f"{minutes:02d}:{seconds:02d}")
        
        # Обновление режима
        if self.timer_state["is_running"]:
            mode_text = "Работаем!" if self.timer_state["is_work_time"] else "Перерыв"
        else:
            mode_text = "Готов к работе" if self.timer_state["is_work_time"] else "Перерыв"
        
        self.mode_label.config(text=mode_text)
        
        # Обновление кнопок
        self.start_btn.config(state="normal" if not self.timer_state["is_running"] and self.timer_state.get("current_task_id") else "disabled")
        self.pause_btn.config(state="normal" if self.timer_state["is_running"] else "disabled")
        
        # Обновление настроек
        self.work_duration.set(str(self.timer_state["work_duration"] // 60))
        self.break_duration.set(str(self.timer_state["break_duration"] // 60))

    def update_tasks_display(self):
        """Обновление отображения задач"""
        self.tasks_listbox.delete(0, tk.END)
        for task in self.tasks:
            display_text = f"{task['name']} ({task['completed_today']}/{task['target_pomodoros']})"
            self.tasks_listbox.insert(tk.END, display_text)
            
            # Выделяем текущую задачу
            if task['id'] == self.timer_state.get('current_task_id'):
                self.tasks_listbox.selection_set(tk.END)

    def start_timer_click(self):
        """Обработчик нажатия кнопки Старт"""
        asyncio.create_task(self.start_timer())

    def pause_timer_click(self):
        """Обработчик нажатия кнопки Пауза"""
        asyncio.create_task(self.pause_timer())

    def skip_timer_click(self):
        """Обработчик нажатия кнопки Пропустить"""
        asyncio.create_task(self.skip_timer())

    def select_task(self):
        """Выбор задачи"""
        selection = self.tasks_listbox.curselection()
        if selection:
            task_id = self.tasks[selection[0]]['id']
            asyncio.create_task(self.set_current_task(task_id))
            
            # Обновляем отображение текущей задачи
            task = self.tasks[selection[0]]
            self.task_label.config(text=f"Текущая задача: {task['name']}")

    def add_pomodoro_click(self):
        """Добавление помидора"""
        selection = self.tasks_listbox.curselection()
        if selection:
            task_id = self.tasks[selection[0]]['id']
            duration = int(self.work_duration.get())
            asyncio.create_task(self.add_pomodoro(task_id, duration))

    def refresh_tasks(self):
        """Обновление списка задач"""
        asyncio.create_task(self.load_tasks())

    async def timer_loop(self):
        """Основной цикл таймера"""
        while self.is_running:
            try:
                # Загружаем состояние с сервера
                await self.load_timer_state()
                await self.load_tasks()
                
                # Обновляем UI в главном потоке
                if self.root:
                    self.root.after(0, self.update_timer_display)
                    self.root.after(0, self.update_tasks_display)
                
                # Проверяем завершение таймера
                if self.timer_state["time_left"] == 0 and self.timer_state["is_running"]:
                    if self.timer_state["is_work_time"]:
                        # Завершение работы
                        self.show_notification("Помидор завершен!", "Время отдохнуть!", "work")
                        # Добавляем помидор к задаче
                        if self.timer_state.get("current_task_id"):
                            await self.add_pomodoro(self.timer_state["current_task_id"], 
                                                   self.timer_state["work_duration"] // 60)
                    else:
                        # Завершение перерыва
                        self.show_notification("Перерыв завершен!", "Время работать!", "break")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Timer loop error: {e}")
                await asyncio.sleep(5)  # Ждем 5 секунд при ошибке

    def run(self):
        """Запуск приложения"""
        # Создаем главное окно
        self.create_main_window()
        
        # Создаем иконку в трее
        tray_icon = self.create_tray_icon()
        
        # Запускаем цикл таймера в отдельном потоке
        def run_timer_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.timer_loop())
        
        timer_thread = threading.Thread(target=run_timer_loop, daemon=True)
        timer_thread.start()
        
        # Запускаем иконку в трее в отдельном потоке
        def run_tray():
            tray_icon.run()
        
        tray_thread = threading.Thread(target=run_tray, daemon=True)
        tray_thread.start()
        
        # Запускаем главное окно
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit_app()

if __name__ == "__main__":
    app = PomodoroDesktopApp()
    app.run()
