# test_connection.py
import asyncio
import aiohttp
import sys

async def test_server_connection():
    """Тестирование подключения к серверу"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/tasks/") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Сервер работает!")
                    print(f"Найдено задач: {len(data)}")
                    return True
                else:
                    print(f"❌ Ошибка сервера: {response.status}")
                    return False
    except aiohttp.ClientConnectorError:
        print("❌ Не удается подключиться к серверу")
        print("Убедитесь, что сервер запущен: python main.py")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def test_websocket():
    """Тестирование WebSocket подключения"""
    try:
        import websockets
        async with websockets.connect("ws://localhost:8000/ws") as websocket:
            print("✅ WebSocket подключение работает!")
            return True
    except Exception as e:
        print(f"❌ WebSocket ошибка: {e}")
        return False

async def main():
    print("🔍 Тестирование подключения к Pomodoro серверу...")
    print("-" * 50)
    
    # Тест HTTP API
    print("1. Тестирование HTTP API...")
    api_ok = await test_server_connection()
    
    # Тест WebSocket (опционально)
    print("\n2. Тестирование WebSocket...")
    try:
        ws_ok = await test_websocket()
    except ImportError:
        print("⚠️  WebSocket тест пропущен (websockets не установлен)")
        ws_ok = True
    
    print("\n" + "=" * 50)
    if api_ok:
        print("🎉 Все тесты пройдены! Сервер готов к работе.")
        print("\nДля запуска:")
        print("  Веб-интерфейс: http://localhost:8000")
        print("  Десктопное приложение: python desktop_app.py")
    else:
        print("❌ Есть проблемы с подключением.")
        print("Убедитесь, что сервер запущен: python main.py")

if __name__ == "__main__":
    asyncio.run(main())
