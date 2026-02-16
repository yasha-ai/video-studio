# Preview & Playback - Предпросмотр видео

## Обзор

Preview Panel предоставляет интерфейс для предпросмотра видео перед публикацией с детальной информацией о файле.

## Функциональность

### 1. Full Video Playback

Открытие видео в системном медиаплеере:

- **macOS**: QuickTime Player (`open`)
- **Windows**: Windows Media Player (`start`)
- **Linux**: VLC / MPV / xdg-open (auto-detect)

### 2. Quick Preview

Быстрый просмотр первых 30 секунд:

- Создаёт временный файл `video_preview_30s.mp4`
- Использует `ffmpeg -t 30 -c copy` (без перекодирования)
- Открывается автоматически в плеере

### 3. Video Information

Детальная информация о файле через ffprobe:

```
📹 Информация о видео

📁 Файл: my_video.mp4
📏 Размер: 125.3 MB
⏱️ Длительность: 5:45

🎥 Разрешение: 1920x1080
🎞️ Кодек: h264
📊 Битрейт: 5.5 Mbps
🎬 FPS: 30.00 fps

📍 Путь: /full/path/to/video.mp4
```

### 4. Folder Navigation

Быстрый доступ к папке с видео через системный файловый менеджер.

## API

### PreviewPanel

```python
from ui.preview_panel import PreviewPanel

panel = PreviewPanel(
    parent,
    on_preview_error=callback  # Optional[Callable[[str], None]]
)

# Загрузить видео
panel.load_video(Path("video.mp4"))
```

### Error Handling

```python
def on_preview_error(error_msg: str):
    """Вызывается при ошибках воспроизведения"""
    logger.error(f"Preview failed: {error_msg}")
```

## Технические детали

### FFprobe Integration

Получение метаданных видео:

```bash
ffprobe -v error \
  -show_entries format=duration,size,bit_rate \
  -show_entries stream=width,height,codec_name,r_frame_rate \
  -of default=noprint_wrappers=1 \
  video.mp4
```

### Supported Players (Linux)

Приоритет авто-обнаружения:

1. **xdg-open** - системный по умолчанию
2. **vlc** - VLC Media Player
3. **mpv** - MPV Player
4. **mplayer** - MPlayer (fallback)

### Quick Preview Pipeline

```
1. ffmpeg -i input.mp4 -t 30 -c copy output_preview_30s.mp4
2. Open output in system player
3. No re-encoding (fast!)
```

## Форматирование данных

### File Size

```python
_format_size(125829120)  # → "120.0 MB"
_format_size(1536)       # → "1.5 KB"
_format_size(1073741824) # → "1.0 GB"
```

### Duration

```python
_format_duration(345)    # → "5:45"
_format_duration(3665)   # → "1:01:05"
_format_duration(30)     # → "0:30"
```

### Bitrate

```python
_format_bitrate(5500000) # → "5.5 Mbps"
_format_bitrate(128000)  # → "128 kbps"
_format_bitrate(0)       # → "N/A"
```

### FPS

```python
_format_fps("30/1")      # → "30.00 fps"
_format_fps("60000/1001") # → "59.94 fps"
_format_fps("24000/1001") # → "23.98 fps"
```

## UI Components

### Preview Zone

- **Icon**: 🎬 (120pt)
- **Background**: `#1a1a1a`
- **Corner radius**: 10px
- **Centered**: relx=0.5, rely=0.4

### Controls

| Button | Action | Hotkey |
|--------|--------|--------|
| ▶️ Открыть в плеере | Full playback | - |
| ⚡ Быстрый просмотр | First 30s | - |
| 📂 Открыть папку | Navigate to folder | - |

### Info Panel

- **Height**: 120px
- **Font**: 12pt monospace
- **State**: Read-only (disabled after load)
- **Scroll**: Automatic if content > height

## Примеры использования

### Базовое использование

```python
# 1. Создать панель
preview = PreviewPanel(parent)

# 2. Загрузить видео
preview.load_video(Path("final_video.mp4"))

# 3. Пользователь кликает "Открыть в плеере"
# 4. Видео открывается в VLC/QuickTime/WMP
```

### С обработкой ошибок

```python
def handle_error(error: str):
    if "ffprobe" in error:
        messagebox.showwarning(
            "FFmpeg Required",
            "Please install FFmpeg to view video info"
        )
    else:
        logger.error(error)

preview = PreviewPanel(
    parent,
    on_preview_error=handle_error
)
```

### Интеграция с Timeline

```python
# После обрезки в Timeline → автоматический Preview
def on_video_trimmed(output_path: str):
    preview_panel.load_video(Path(output_path))
    preview_panel._play_video()  # Автоматический запуск

timeline.on_video_edited = on_video_trimmed
```

## Тестирование

```bash
# Запуск тестов
python3 -m unittest tests.test_preview_panel -v
```

### Test Coverage

- ✅ `test_format_size` - форматирование байтов
- ✅ `test_format_duration` - форматирование секунд
- ✅ `test_format_bitrate` - форматирование битрейта
- ✅ `test_format_fps` - парсинг FPS (fraction format)

## Зависимости

- **customtkinter** - UI framework
- **ffprobe** - метаданные видео
- **ffmpeg** - quick preview generation
- **System media player** - воспроизведение

## Cross-platform Support

| Platform | Default Player | Alternative |
|----------|---------------|-------------|
| macOS | QuickTime (`open`) | VLC via `brew` |
| Windows | Windows Media Player | VLC |
| Linux | xdg-open | VLC, MPV, MPlayer |

## Ограничения

- Воспроизведение через системный плеер (не встроенный)
- Требуется ffmpeg/ffprobe для информации
- Quick Preview создаёт временный файл

## Roadmap

- [ ] Встроенный video player (Pillow + OpenCV)
- [ ] Thumbnail preview (frame extraction)
- [ ] Scrubbing timeline (seek to position)
- [ ] Volume control
- [ ] Playback speed control
- [ ] A/B comparison (before/after trim)
