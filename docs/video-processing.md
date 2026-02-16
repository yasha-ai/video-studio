# Video Processing (ffmpeg)

## Обзор

VideoProcessor — модуль обработки видео через ffmpeg. Предоставляет все основные операции для редактирования видео, необходимые для Video Studio.

## Возможности

### 1. Склейка видео (Concat)
Объединение нескольких видеофайлов в один:
- Intro + Main Video + Outro
- Автоматическая склейка без перекодирования (быстро)
- Поддержка произвольного количества видео

### 2. Обрезка видео (Trim)
Нарезка видео по времени:
- Указание времени начала и окончания
- Copy-режим (без перекодирования)
- Сохранение качества

### 3. Извлечение аудио (Extract Audio)
Отделение звука от видео:
- Форматы: MP3, WAV, AAC
- Настройка битрейта
- Качественное извлечение

### 4. Оверлей видео (Picture-in-Picture)
Наложение видео поверх основного:
- Настройка позиции (x, y)
- Изменение размера оверлея
- Регулировка прозрачности (opacity)
- Ideal для вебкам-оверлея

### 5. Микширование аудио (Audio Mix)
Наложение одного аудио на другое:
- Регулировка громкости наложенного звука
- Автоматическое микширование
- Полезно для фоновой музыки

### 6. Объединение видео и аудио (Merge)
Замена звуковой дорожки:
- Видео без звука + новый звук = финальное видео
- Быстрая операция (copy video stream)
- AAC аудиокодек

## Архитектура

```
VideoProcessor
├── _check_ffmpeg()         # Проверка наличия ffmpeg
├── get_video_info()        # Получение метаданных (duration, resolution, fps)
├── concat_videos()         # Склейка видео
├── trim_video()            # Обрезка видео
├── extract_audio()         # Извлечение аудио
├── overlay_video()         # Оверлей видео
├── overlay_audio()         # Микширование аудио
└── merge_video_audio()     # Объединение видео и аудио
```

## Интеграция с Artifacts System

Все выходные файлы автоматически сохраняются в систему артефактов:
- **Видео:** `output/artifacts/project_name/video/`
- **Аудио:** `output/artifacts/project_name/audio/`
- **Метаданные:** JSON с параметрами обработки

## API Reference

### VideoProcessor

#### `__init__(artifacts: ArtifactsManager)`
Инициализация процессора.

**Args:**
- `artifacts`: Менеджер артефактов проекта

**Raises:**
- `RuntimeError`: Если ffmpeg не установлен

---

#### `get_video_info(video_path: str) -> VideoInfo`
Получить информацию о видеофайле.

**Args:**
- `video_path`: Путь к видеофайлу

**Returns:**
- `VideoInfo`: Объект с параметрами видео
  - `duration: float` — длительность (секунды)
  - `width: int` — ширина (пиксели)
  - `height: int` — высота (пиксели)
  - `codec: str` — видеокодек
  - `fps: float` — FPS
  - `has_audio: bool` — наличие аудио

**Example:**
```python
info = processor.get_video_info("video.mp4")
print(f"Duration: {info.duration}s, Resolution: {info.width}x{info.height}")
```

---

#### `concat_videos(videos: List[str], output_name: str = "merged_video") -> str`
Склейка нескольких видео в одно.

**Args:**
- `videos`: Список путей к видео для склейки
- `output_name`: Название выходного артефакта (default: "merged_video")
- `progress_callback`: Опциональный колбэк для прогресса

**Returns:**
- `str`: Путь к склеенному видео

**Raises:**
- `ValueError`: Если список видео пуст
- `RuntimeError`: Если ffmpeg вернул ошибку

**Example:**
```python
result = processor.concat_videos([
    "intro.mp4",
    "main_video.mp4",
    "outro.mp4"
], "final_merged")
```

---

#### `trim_video(input_path: str, start_time: float, end_time: float, output_name: str = "trimmed_video") -> str`
Обрезка видео по времени.

**Args:**
- `input_path`: Путь к исходному видео
- `start_time`: Время начала (секунды)
- `end_time`: Время окончания (секунды)
- `output_name`: Название артефакта (default: "trimmed_video")

**Returns:**
- `str`: Путь к обрезанному видео

**Example:**
```python
# Обрезать с 10 по 30 секунду
result = processor.trim_video("video.mp4", 10.0, 30.0, "trimmed")
```

---

#### `extract_audio(video_path: str, output_name: str = "original_audio", format: str = "mp3", bitrate: str = "192k") -> str`
Извлечение аудио из видео.

**Args:**
- `video_path`: Путь к видео
- `output_name`: Название артефакта (default: "original_audio")
- `format`: Формат аудио: "mp3", "wav", "aac" (default: "mp3")
- `bitrate`: Битрейт (default: "192k")

**Returns:**
- `str`: Путь к извлеченному аудио

**Example:**
```python
audio = processor.extract_audio("video.mp4", "audio", format="mp3", bitrate="192k")
```

---

#### `overlay_video(base_video: str, overlay_video: str, position: Tuple[int, int] = (10, 10), size: Optional[Tuple[int, int]] = None, opacity: float = 1.0, output_name: str = "overlay_video") -> str`
Наложение видео поверх основного (Picture-in-Picture).

**Args:**
- `base_video`: Путь к основному видео
- `overlay_video`: Путь к оверлейному видео (например, вебкам)
- `position`: Позиция (x, y) в пикселях (default: (10, 10))
- `size`: Размер оверлея (width, height). None = оригинальный размер
- `opacity`: Прозрачность (0.0 - 1.0) (default: 1.0)
- `output_name`: Название артефакта (default: "overlay_video")

**Returns:**
- `str`: Путь к видео с оверлеем

**Example:**
```python
# Вебкам в правом верхнем углу, 640x360, полупрозрачный
result = processor.overlay_video(
    base_video="screen_recording.mp4",
    overlay_video="webcam.mp4",
    position=(1280 - 640 - 20, 20),  # 20px отступ от правого верхнего угла
    size=(640, 360),
    opacity=0.9,
    output_name="final_with_cam"
)
```

---

#### `overlay_audio(base_audio: str, overlay_audio: str, overlay_volume: float = 1.0, output_name: str = "mixed_audio", format: str = "mp3") -> str`
Микширование аудио (наложение одного на другое).

**Args:**
- `base_audio`: Основное аудио (голос)
- `overlay_audio`: Накладываемое аудио (фоновая музыка)
- `overlay_volume`: Громкость наложенного аудио (0.0 - 1.0) (default: 1.0)
- `output_name`: Название артефакта (default: "mixed_audio")
- `format`: Формат выходного аудио (default: "mp3")

**Returns:**
- `str`: Путь к смикшированному аудио

**Example:**
```python
# Голос + тихая фоновая музыка (20% громкости)
result = processor.overlay_audio(
    base_audio="voice.mp3",
    overlay_audio="background_music.mp3",
    overlay_volume=0.2,  # 20% от оригинальной громкости
    output_name="mixed"
)
```

---

#### `merge_video_audio(video_path: str, audio_path: str, output_name: str = "final_video") -> str`
Объединение видео и аудио (замена звуковой дорожки).

**Args:**
- `video_path`: Путь к видео (без звука или с заменяемым звуком)
- `audio_path`: Путь к аудио
- `output_name`: Название артефакта (default: "final_video")

**Returns:**
- `str`: Путь к итоговому видео

**Example:**
```python
# Видео с очищенным звуком
result = processor.merge_video_audio(
    video_path="video_no_audio.mp4",
    audio_path="cleaned_audio.mp3",
    output_name="final_video"
)
```

---

## CLI Usage

VideoProcessor имеет встроенный CLI для тестирования:

```bash
# Склейка видео
python src/processors/video_processor.py \
  --project "test_project" \
  --action concat \
  --inputs intro.mp4 main.mp4 outro.mp4 \
  --output merged

# Обрезка видео
python src/processors/video_processor.py \
  --project "test_project" \
  --action trim \
  --input video.mp4 \
  --start 10.0 \
  --end 30.0 \
  --output trimmed

# Извлечение аудио
python src/processors/video_processor.py \
  --project "test_project" \
  --action extract_audio \
  --input video.mp4 \
  --output audio

# Объединение видео и аудио
python src/processors/video_processor.py \
  --project "test_project" \
  --action merge \
  --input video.mp4 \
  --audio cleaned_audio.mp3 \
  --output final
```

## Требования

- **ffmpeg** версии 4.0+ (установлено на сервере)
- **ffprobe** (входит в комплект ffmpeg)

Установка (если нужно):
```bash
sudo apt install ffmpeg
```

## Performance

- **Concat:** Быстро (copy codec, без перекодирования)
- **Trim:** Быстро (copy codec)
- **Extract Audio:** Средне (аудиокодек перекодируется)
- **Overlay Video:** Медленно (полное перекодирование)
- **Overlay Audio:** Средне (амикс фильтр)
- **Merge:** Быстро (copy video stream, перекодировка только аудио)

## Testing

Unit-тесты: `tests/test_video_processor.py`

Запуск:
```bash
pytest tests/test_video_processor.py -v
```

**Результаты:**
- 12 unit-тестов ✅
- Покрытие: все основные функции
- Мокирование ffmpeg для быстрых тестов

Integration tests (требуют реального ffmpeg):
```bash
pytest tests/test_video_processor.py -v -m integration
```

## Error Handling

Все методы выбрасывают исключения при ошибках:
- `ValueError`: Некорректные параметры
- `RuntimeError`: Ошибка ffmpeg
- `FileNotFoundError`: Файл не найден

**Пример обработки:**
```python
try:
    result = processor.trim_video("video.mp4", 10.0, 30.0)
except RuntimeError as e:
    print(f"FFmpeg error: {e}")
except ValueError as e:
    print(f"Invalid parameters: {e}")
```

## Roadmap

**Реализовано:**
- ✅ Склейка видео
- ✅ Обрезка видео
- ✅ Извлечение аудио
- ✅ Оверлей видео (PiP)
- ✅ Микширование аудио
- ✅ Объединение видео и аудио
- ✅ Интеграция с Artifacts System
- ✅ Unit-тесты

**Будущие улучшения:**
- [ ] Progress tracking (парсинг ffmpeg stderr)
- [ ] Batch processing (обработка нескольких видео)
- [ ] Video filters (цветокоррекция, контраст, яркость)
- [ ] Advanced trimming (несколько сегментов)
- [ ] GPU acceleration (NVENC/VAAPI)

## Пример использования в workflow

```python
from src.core.artifacts import ArtifactsManager
from src.processors.video_processor import VideoProcessor

# Инициализация
artifacts = ArtifactsManager("my_youtube_video")
processor = VideoProcessor(artifacts)

# 1. Склейка: intro + main + outro
merged = processor.concat_videos([
    "intro.mp4",
    "main_recording.mp4",
    "outro.mp4"
], "merged_video")

# 2. Извлечение звука
audio = processor.extract_audio(merged, "original_audio")

# 3. Очистка аудио (выполняется другим модулем)
# cleaned_audio = audio_cleaner.clean(audio)

# 4. Объединение видео с очищенным звуком
final = processor.merge_video_audio(
    merged, 
    "cleaned_audio.mp3",  # предполагается уже очищено
    "final_video"
)

print(f"Final video ready: {final}")
```
