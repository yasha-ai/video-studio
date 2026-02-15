# Installation Guide

## Requirements

- **Python 3.10+**
- **Tkinter** (для GUI)
- **ffmpeg** (для видеообработки)

### Установка зависимостей (Linux)

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-tk python3-dev ffmpeg

# Fedora
sudo dnf install python3-tkinter ffmpeg

# Arch
sudo pacman -S tk ffmpeg
```

### Установка зависимостей (macOS)

```bash
# Homebrew
brew install python-tk ffmpeg
```

### Установка зависимостей (Windows)

- Python из официального сайта уже включает Tkinter
- Скачайте FFmpeg: https://ffmpeg.org/download.html

## Setup

```bash
# Клонировать репозиторий (или перейти в папку проекта)
cd video-studio

# Создать виртуальное окружение
python3 -m venv venv

# Активировать виртуальное окружение
# Linux/macOS:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Скопировать .env.example в .env и заполнить API ключи
cp .env.example .env
nano .env  # или любой другой редактор
```

## Running

```bash
# Убедитесь, что виртуальное окружение активно
source venv/bin/activate  # Linux/macOS
# или venv\Scripts\activate  # Windows

# Запустить приложение
python src/main.py
```

## Troubleshooting

### "ModuleNotFoundError: No module named '_tkinter'"

**Проблема:** Python не скомпилирован с поддержкой Tkinter.

**Решение:**
- **Linux:** Установите `python3-tk` (см. выше)
- **macOS:** `brew install python-tk`
- **Windows:** Переустановите Python с галочкой "tcl/tk and IDLE"

### "ffmpeg: command not found"

**Проблема:** FFmpeg не установлен или не в PATH.

**Решение:** Установите ffmpeg (см. выше) и убедитесь, что он доступен:

```bash
ffmpeg -version
```

### GUI не запускается на удаленном сервере

**Проблема:** Video Studio — это десктопное приложение, требующее графическое окружение (X11/Wayland).

**Решение:** Запускайте на локальной машине с графическим интерфейсом. Для headless-серверов GUI недоступен.

## Development

```bash
# Проверка импортов (без GUI)
python -c "from config.settings import Settings; print('✅ Settings OK')"

# Структура проекта
video-studio/
├── src/           # Исходный код
├── config/        # Конфигурация
├── assets/        # Ресурсы (шрифты, иконки)
├── output/        # Выходные файлы
└── venv/          # Виртуальное окружение
```
