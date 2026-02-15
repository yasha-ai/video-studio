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

## Установка

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Запуск

```bash
python src/main.py
```

## Документация

См. [SPEC.md](SPEC.md) для детальной спецификации.
