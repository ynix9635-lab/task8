import ctypes
import time
import os
import random

# --- ОПРЕДЕЛЕНИЕ НИЗКОУРОВНЕВЫХ СТРУКТУР WINDOWS API ---
class COORD(ctypes.Structure):
    _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

class SMALL_RECT(ctypes.Structure):
    _fields_ = [
        ("Left", ctypes.c_short), ("Top", ctypes.c_short),
        ("Right", ctypes.c_short), ("Bottom", ctypes.c_short)
    ]

# Объединение (union) для символа: делит память между ASCII и Unicode
class CHAR_UNION(ctypes.Union):
    _fields_ = [("UnicodeChar", ctypes.c_wchar), ("AsciiChar", ctypes.c_char)]

# Структура ячейки буфера экрана (ровно 4 байта в ОЗУ)
class CHAR_INFO(ctypes.Structure):
    _fields_ = [("Char", CHAR_UNION), ("Attributes", ctypes.c_ushort)]

# --- КОНСТАНТЫ ЦВЕТОВЫХ АТРИБУТОВ ---
FOREGROUND_BLUE      = 0x0001
FOREGROUND_GREEN     = 0x0002
FOREGROUND_RED       = 0x0004
FOREGROUND_INTENSITY = 0x0008
BACKGROUND_BLUE      = 0x0010
BACKGROUND_GREEN     = 0x0020
BACKGROUND_RED       = 0x0040
BACKGROUND_INTENSITY = 0x0080

# Смешиваем маски для получения ярких цветов
COLOR_TEXT_WHITE  = FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE | FOREGROUND_INTENSITY
COLOR_TEXT_GREEN  = FOREGROUND_GREEN | FOREGROUND_INTENSITY
COLOR_TEXT_RED    = FOREGROUND_RED | FOREGROUND_INTENSITY
COLOR_BG_NAVY     = BACKGROUND_BLUE | BACKGROUND_INTENSITY

# Подключаем библиотеку ядра Windows
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

# Размеры нашего окна (матрицы экрана)
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 25

# 1. Получаем дескриптор оригинального буфера экрана, чтобы восстановить его в конце
h_original_out = kernel32.GetStdHandle(-11) # STD_OUTPUT_HANDLE = -11

print("[СИСТЕМА] Запрашиваем у ядра создание дополнительного скрытого буфера экрана (бэк-буфера)...")
# 2. Вызываем CreateConsoleScreenBuffer (параметры доступа: чтение/запись, режим разделения)
h_back_buffer = kernel32.CreateConsoleScreenBuffer(
    0x80000000 | 0x40000000, # GENERIC_READ | GENERIC_WRITE
    0, None, 1, None         # CONSOLE_TEXTMODE_BUFFER = 1
)

if h_back_buffer == -1 or h_back_buffer is None:
    print(f"[ОШИБКА] Не удалось создать буфер экрана. Код: {ctypes.get_last_error()}")
    exit(1)

# Переключаем видеокарту на отображение нашего нового буфера
kernel32.SetConsoleActiveScreenBuffer(h_back_buffer)

# 3. Выделяем локальный плоский массив в памяти Ring 3 под размер матрицы экрана
buffer_size = SCREEN_WIDTH * SCREEN_HEIGHT
local_memory_buffer = (CHAR_INFO * buffer_size)()

def clear_local_buffer(char=' ', attr=0):
    """Метод быстрой очистки локального буфера в памяти процесса"""
    for i in range(buffer_size):
        local_memory_buffer[i].Char.UnicodeChar = char
        local_memory_buffer[i].Attributes = attr

def write_string(text, x, y, attr):
    """Функция посимвольной записи строки в локальную матрицу памяти"""
    if y < 0 or y >= SCREEN_HEIGHT: return
    start_index = y * SCREEN_WIDTH + x
    for idx, char in enumerate(text):
        if x + idx >= SCREEN_WIDTH: break
        local_memory_buffer[start_index + idx].Char.UnicodeChar = char
        local_memory_buffer[start_index + idx].Attributes = attr

# Координаты буфера и прямоугольник вывода для системной функции WriteConsoleOutputW
buffer_size_coord = COORD(SCREEN_WIDTH, SCREEN_HEIGHT)
buffer_coord = COORD(0, 0)
write_region = SMALL_RECT(0, 0, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1)

# Анимационные символы (фазы вращения кулера)
fan_frames = ['|', '/', '-', '']
frame_idx = 0

print("[ПРОЦЕССОР] Запуск высокопроизводительного цикла отрисовки кадра...")
try:
    for tick in range(100): # Симулируем 100 кадров анимации
        # Шаг А: Быстро очищаем бэк-буфер в памяти (устанавливаем темно-синий фон)
        clear_local_buffer(' ', COLOR_BG_NAVY)
        
        # Шаг Б: Заполняем матрицу элементами интерфейса
        write_string("=== НИЗКОУРОВНЕВЫЙ МОНИТОР БУФЕРА ЭКРАНА (WINDOWS API) ===", 12, 2, COLOR_TEXT_WHITE | COLOR_BG_NAVY)
        write_string(f"Текущий кадр рендеринга: {tick:03d} / 100", 5, 5, COLOR_TEXT_GREEN | COLOR_BG_NAVY)
        
        # Симулируем случайное изменение условного датчика
        current_data = random.randint(1100, 1600)
        status_color = COLOR_TEXT_GREEN if current_data > 1200 else COLOR_TEXT_RED
        
        write_string(f"Показания системного датчика: {current_data} ед.", 5, 7, COLOR_TEXT_WHITE | COLOR_BG_NAVY)
        
        # Рисуем вращающийся элемент (кулер)
        current_frame = fan_frames[frame_idx]
        write_string(f"Статус кулера: [ {current_frame} ] ACTIVE", 5, 9, status_color | COLOR_BG_NAVY)
        
        # Делаем декоративную рамку из символов с флагами сетки
        for x in range(2, 78):
            local_memory_buffer[4 * SCREEN_WIDTH + x].Attributes |= 0x0100 # Линия над символом
            local_memory_buffer[12 * SCREEN_WIDTH + x].Attributes |= 0x0100 # Линия над символом

        frame_idx = (frame_idx + 1) % len(fan_frames)

        # Шаг В: СИСТЕМНЫЙ ВЫЗОВ. Копируем всю подготовленную матрицу в ядро ОС за одну команду
        kernel32.WriteConsoleOutputW(
            h_back_buffer,
            ctypes.byref(local_memory_buffer),
            buffer_size_coord,
            buffer_coord,
            ctypes.byref(write_region)
        )
        """os.system('cls')  # очистка экрана системной командой

        print("=== НИЗКОУРОВНЕВЫЙ МОНИТОР БУФЕРА ЭКРАНА (WINDOWS API) ===")
        print()
        print(f"Текущий кадр рендеринга: {tick:03d} / 100")
        print()
        print(f"Показания системного датчика: {current_data} ед.")
        print()
        print(f"Статус кулера: [ {current_frame} ] ACTIVE")
        print()
        print("------------------------------------------------------------")
        print("------------------------------------------------------------")"""
        # Искусственная задержка между кадрами (50 миллисекунд)
        time.sleep(0.05)

finally:
    # Обязательный шаг восстановления: возвращаем терминал в исходное состояние
    kernel32.SetConsoleActiveScreenBuffer(h_original_out)
    kernel32.CloseHandle(h_back_buffer)
    print("n[СИСТЕМА] Оригинальный буфер экрана восстановлен. Ресурсы ядра очищены.")