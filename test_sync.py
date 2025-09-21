# test_sync.py
import asyncio
import aiohttp
import time
import json

async def test_timer_sync():
    """Тестирование синхронизации таймера между клиентами"""
    print("🔄 Тестирование синхронизации таймера...")
    
    async with aiohttp.ClientSession() as session:
        # 1. Получаем начальное состояние
        print("1. Получение начального состояния...")
        async with session.get("http://localhost:8000/api/timer/") as response:
            if response.status == 200:
                initial_state = await response.json()
                print(f"   Начальное состояние: {initial_state}")
            else:
                print("   ❌ Ошибка получения состояния")
                return False
        
        # 2. Запускаем таймер
        print("2. Запуск таймера...")
        async with session.post("http://localhost:8000/api/timer/start/") as response:
            if response.status == 200:
                print("   ✅ Таймер запущен")
            else:
                print("   ❌ Ошибка запуска таймера")
                return False
        
        # 3. Ждем несколько секунд
        print("3. Ожидание 3 секунды...")
        await asyncio.sleep(3)
        
        # 4. Проверяем состояние
        print("4. Проверка состояния после ожидания...")
        async with session.get("http://localhost:8000/api/timer/") as response:
            if response.status == 200:
                current_state = await response.json()
                print(f"   Текущее состояние: {current_state}")
                
                # Проверяем, что время уменьшилось
                if current_state["time_left"] < initial_state["time_left"]:
                    print("   ✅ Время корректно уменьшилось")
                else:
                    print("   ❌ Время не изменилось")
                    return False
            else:
                print("   ❌ Ошибка получения состояния")
                return False
        
        # 5. Пауза таймера
        print("5. Пауза таймера...")
        async with session.post("http://localhost:8000/api/timer/pause/") as response:
            if response.status == 200:
                print("   ✅ Таймер поставлен на паузу")
            else:
                print("   ❌ Ошибка паузы таймера")
                return False
        
        # 6. Ждем еще секунду
        print("6. Ожидание 1 секунда...")
        await asyncio.sleep(1)
        
        # 7. Проверяем, что время не изменилось
        print("7. Проверка, что время не изменилось на паузе...")
        async with session.get("http://localhost:8000/api/timer/") as response:
            if response.status == 200:
                paused_state = await response.json()
                print(f"   Состояние на паузе: {paused_state}")
                
                if paused_state["time_left"] == current_state["time_left"]:
                    print("   ✅ Время корректно заморожено на паузе")
                else:
                    print("   ❌ Время изменилось на паузе")
                    return False
            else:
                print("   ❌ Ошибка получения состояния")
                return False
        
        print("\n🎉 Все тесты синхронизации пройдены!")
        return True

async def test_multiple_clients():
    """Тестирование синхронизации между несколькими клиентами"""
    print("\n🔄 Тестирование синхронизации между клиентами...")
    
    # Симулируем два клиента
    async with aiohttp.ClientSession() as client1, aiohttp.ClientSession() as client2:
        # Клиент 1 запускает таймер
        print("Клиент 1: Запуск таймера...")
        async with client1.post("http://localhost:8000/api/timer/start/") as response:
            if response.status != 200:
                print("❌ Ошибка запуска таймера")
                return False
        
        # Ждем немного
        await asyncio.sleep(2)
        
        # Клиент 2 проверяет состояние
        print("Клиент 2: Проверка состояния...")
        async with client2.get("http://localhost:8000/api/timer/") as response:
            if response.status == 200:
                state = await response.json()
                print(f"   Состояние: {state}")
                if state["is_running"]:
                    print("   ✅ Клиент 2 видит, что таймер запущен")
                else:
                    print("   ❌ Клиент 2 не видит запущенный таймер")
                    return False
            else:
                print("   ❌ Ошибка получения состояния")
                return False
        
        # Клиент 2 ставит на паузу
        print("Клиент 2: Пауза таймера...")
        async with client2.post("http://localhost:8000/api/timer/pause/") as response:
            if response.status != 200:
                print("❌ Ошибка паузы таймера")
                return False
        
        # Клиент 1 проверяет, что таймер на паузе
        print("Клиент 1: Проверка паузы...")
        async with client1.get("http://localhost:8000/api/timer/") as response:
            if response.status == 200:
                state = await response.json()
                if not state["is_running"]:
                    print("   ✅ Клиент 1 видит, что таймер на паузе")
                else:
                    print("   ❌ Клиент 1 не видит паузу")
                    return False
            else:
                print("   ❌ Ошибка получения состояния")
                return False
        
        print("✅ Синхронизация между клиентами работает!")
        return True

async def main():
    print("🧪 Тестирование синхронизации Pomodoro Timer")
    print("=" * 50)
    
    try:
        # Тест 1: Базовая синхронизация
        sync_ok = await test_timer_sync()
        
        if sync_ok:
            # Тест 2: Множественные клиенты
            multi_ok = await test_multiple_clients()
            
            if multi_ok:
                print("\n🎉 Все тесты пройдены!")
                print("\nТеперь вы можете:")
                print("1. Запустить сервер: python main.py")
                print("2. Открыть веб-интерфейс: http://localhost:8000")
                print("3. Запустить десктопное приложение: python desktop_app.py")
                print("4. Таймер будет синхронизироваться между всеми интерфейсами!")
            else:
                print("\n❌ Тесты множественных клиентов не прошли")
        else:
            print("\n❌ Базовые тесты синхронизации не прошли")
            
    except Exception as e:
        print(f"\n❌ Ошибка тестирования: {e}")
        print("Убедитесь, что сервер запущен: python main.py")

if __name__ == "__main__":
    asyncio.run(main())
