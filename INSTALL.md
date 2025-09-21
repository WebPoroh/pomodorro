# Установка Pomodoro Tracker

## Проблемы и решения

### Проблема 1: Ошибка установки Pillow

**Решение 1 (Рекомендуемое):** Используйте предкомпилированные пакеты:

```bash
pip install -r requirements-windows.txt
```

**Решение 2:** Если все еще есть проблемы с Pillow:

```bash
# Установите Microsoft Visual C++ Build Tools
# Затем:
pip install --upgrade pip
pip install --only-binary=all Pillow
```

**Решение 3:** Используйте conda:

```bash
conda install pillow
pip install -r requirements-windows.txt
```

### Проблема 2: Ошибки импорта

Убедитесь, что вы активировали виртуальное окружение:

```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

## Пошаговая установка

1. **Создайте виртуальное окружение:**
```bash
python -m venv .venv
```

2. **Активируйте его:**
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac  
source .venv/bin/activate
```

3. **Обновите pip:**
```bash
pip install --upgrade pip
```

4. **Установите зависимости:**
```bash
# Попробуйте сначала этот вариант:
pip install -r requirements-windows.txt

# Если не работает, попробуйте:
pip install fastapi uvicorn sqlalchemy aiohttp pystray Pillow websockets
```

5. **Проверьте установку:**
```bash
python test_connection.py
```

## Альтернативная установка

Если проблемы продолжаются, попробуйте:

```bash
# Установите только основные пакеты
pip install fastapi uvicorn sqlalchemy

# Затем остальные по одному
pip install aiohttp
pip install pystray
pip install Pillow
pip install websockets
```

## Запуск

После успешной установки:

1. **Запустите сервер:**
```bash
python main.py
```

2. **Откройте браузер:**
http://localhost:8000

3. **Запустите десктопное приложение (в новом терминале):**
```bash
python desktop_app.py
```

## Устранение неполадок

### Ошибка "No module named 'fastapi'"
- Убедитесь, что виртуальное окружение активировано
- Переустановите: `pip install fastapi`

### Ошибка компиляции Pillow
- Установите Microsoft Visual C++ Build Tools
- Или используйте conda: `conda install pillow`

### Ошибка "NameError: name 'PomodoroResponse'"
- Эта ошибка исправлена в обновленной версии main.py

### Проблемы с pystray
- На Windows может потребоваться: `pip install pystray[win32]`
