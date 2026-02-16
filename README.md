# Video Studio

**Локальное десктопное приложение для полного цикла подготовки видео к публикации на YouTube.**

## Описание

Video Studio — Python-приложение с графическим интерфейсом (CustomTkinter) для:
- Видеомонтажа (склейка, нарезка, оверлеи)
- Транскрибации (Whisper / Gemini API)
- AI очистки аудио (встроенная + Auphonic)
- Генерации заголовков и обложек (AI)
- Загрузки на YouTube

## Технологии

- **Python 3.10+**
- **CustomTkinter** — современный UI
- **ffmpeg-python** / **moviepy** — видеообработка
- **openai-whisper** — локальная транскрибация
- **Google Gemini API** — AI генерация
- **google-api-python-client** — YouTube интеграция

## Требования

- **Python 3.10+**
- **FFmpeg** (для видеообработки)

### Установка FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
Скачайте с [ffmpeg.org](https://ffmpeg.org/download.html) и добавьте в PATH.

## Установка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/yasha-ai/video-studio.git
cd video-studio

# 2. Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt
```

## Запуск

```bash
# Из корня проекта (рекомендуется)
python3 -m src.main

# Или прямой запуск
python3 src/main.py
```

## Документация

См. [SPEC.md](SPEC.md) для детальной спецификации.
