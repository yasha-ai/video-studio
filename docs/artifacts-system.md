# Artifacts System & Modular Workflow

## Обзор

Система артефактов и модульный workflow — ключевые компоненты Video Studio, обеспечивающие:

1. **Управление промежуточными файлами** — все результаты каждого этапа сохраняются и доступны для повторного использования
2. **Модульность** — возможность запускать любой этап независимо
3. **Восстанавливаемость** — можно вернуться к любому шагу и переделать его
4. **Прозрачность** — полная история обработки видео

## Архитектура

### ArtifactsManager

Менеджер артефактов отвечает за хранение всех промежуточных файлов проекта.

**Структура папок:**

```
output/artifacts/
└── project_name_20260215_235959/
    ├── manifest.json              # Манифест проекта
    ├── workflow_state.json        # Состояние workflow
    ├── video/                     # Видеофайлы
    │   ├── original_video.mp4
    │   ├── merged_video.mp4
    │   ├── video_no_audio.mp4
    │   └── final_video.mp4
    ├── audio/                     # Аудиофайлы
    │   ├── original_audio.mp3
    │   ├── cleaned_audio.mp3
    │   ├── auphonic_audio.mp3
    │   └── final_audio.mp3
    ├── transcription/             # Транскрипции
    │   ├── raw_transcription.txt
    │   ├── fixed_transcription.txt
    │   ├── timecodes.json
    │   └── key_moments.json
    ├── titles/                    # Заголовки
    │   ├── titles_list.json
    │   ├── titles_critique.json
    │   └── selected_title.txt
    ├── thumbnails/                # Обложки
    │   ├── thumbnail_1.png
    │   ├── thumbnail_2.png
    │   ├── thumbnail_3.png
    │   ├── thumbnail_4.png
    │   └── selected_thumbnail.png
    └── metadata/                  # Метаданные
        ├── youtube_metadata.json
        └── *_metadata.json
```

**Типы артефактов:**

- **Video:** `original_video`, `intro_video`, `outro_video`, `merged_video`, `video_no_audio`, `final_video`
- **Audio:** `original_audio`, `cleaned_audio`, `auphonic_audio`, `final_audio`
- **Transcription:** `raw_transcription`, `fixed_transcription`, `timecodes`, `key_moments`
- **Titles:** `titles_list`, `titles_critique`, `selected_title`
- **Thumbnails:** `thumbnail_1`, `thumbnail_2`, `thumbnail_3`, `thumbnail_4`, `selected_thumbnail`
- **Metadata:** `youtube_metadata`, и любые дополнительные метаданные

### WorkflowState

Менеджер состояния workflow отслеживает выполнение каждого этапа.

**Этапы workflow:**

1. `import_video` — Импорт исходного видео
2. `edit_trim` — Редактирование и обрезка
3. `transcribe` — Транскрибация аудио
4. `clean_audio` — Очистка аудио (AI / Auphonic)
5. `generate_titles` — Генерация заголовков
6. `create_thumbnail` — Создание обложки
7. `preview` — Предпросмотр финального видео
8. `upload_youtube` — Загрузка на YouTube

**Состояние каждого этапа:**

```json
{
  "enabled": true,      // Включен ли этап
  "completed": false,   // Завершен ли
  "skipped": false,     // Пропущен ли
  "error": null         // Ошибка (если была)
}
```

## Использование

### Пример: Создание проекта

```python
from src.core.artifacts import ArtifactsManager, WorkflowState

# Создаем менеджер артефактов
artifacts = ArtifactsManager("my_youtube_video")

# Создаем workflow
workflow = WorkflowState(artifacts)

# Сохраняем исходное видео
from pathlib import Path
video_path = Path("input/my_video.mp4")
artifacts.save_artifact("original_video", video_path)

# Отмечаем импорт как завершенный
workflow.mark_completed("import_video")
```

### Пример: Работа с артефактами

```python
# Проверка наличия артефакта
if artifacts.has_artifact("original_video"):
    video_path = artifacts.get_artifact("original_video")
    print(f"Video found: {video_path}")

# Список всех артефактов
for artifact in artifacts.list_artifacts():
    print(f"{artifact['name']}: {artifact['size']} bytes")

# Сохранение результата обработки
processed_audio = Path("tmp/cleaned_audio.mp3")
artifacts.save_artifact(
    "cleaned_audio",
    processed_audio,
    metadata={"method": "AI", "quality": "high"}
)

# Удаление артефакта (если нужно пересоздать)
artifacts.delete_artifact("cleaned_audio")
```

### Пример: Управление workflow

```python
# Отключение ненужных этапов
workflow.disable_step("create_thumbnail")  # Пропускаем создание обложки
workflow.disable_step("upload_youtube")    # Не загружаем на YouTube

# Получение следующего этапа
next_step = workflow.get_next_step()
print(f"Next step: {next_step}")

# Отметка завершения
workflow.mark_completed("transcribe")

# Отметка ошибки
workflow.mark_error("clean_audio", "Auphonic API key missing")

# Сброс всех этапов
workflow.reset()

# Сводка по прогрессу
print(workflow.get_summary())
```

## UI Integration

### WorkflowPanel

Панель управления workflow с чекбоксами для включения/отключения этапов.

**Функции:**

- ✓ Чекбоксы для каждого этапа
- ✓ Индикаторы статуса (Pending / Done / Error)
- ✓ Кнопки запуска отдельных этапов
- ✓ Кнопка "Run Selected Steps" для запуска всех выбранных
- ✓ Select All / Deselect All
- ✓ Прогресс-бар (N/M steps completed)

**Использование:**

```python
from src.ui.workflow_panel import WorkflowPanel

# Создание панели
panel = WorkflowPanel(
    parent_widget,
    workflow_state=workflow,
    on_step_toggle=handle_step_toggle,
    on_run_step=handle_run_step,
)

# Обновление статуса после выполнения
panel.set_step_completed("transcribe")

# Отметка ошибки
panel.set_step_error("clean_audio", "API error")

# Полное обновление UI
panel.refresh()
```

## Manifest.json

Манифест проекта содержит полную информацию о всех артефактах:

```json
{
  "project_name": "my_youtube_video",
  "project_id": "my_youtube_video_20260215_235959",
  "created": "20260215_235959",
  "updated": "2026-02-16T00:05:43.123456",
  "artifacts": {
    "original_video": "/path/to/output/artifacts/.../original_video.mp4",
    "cleaned_audio": "/path/to/output/artifacts/.../cleaned_audio.mp3",
    "raw_transcription": "/path/to/output/artifacts/.../raw_transcription.txt",
    ...
  }
}
```

## Workflow State JSON

Состояние workflow сохраняется в `workflow_state.json`:

```json
{
  "steps": {
    "import_video": {
      "enabled": true,
      "completed": true,
      "skipped": false,
      "error": null
    },
    "transcribe": {
      "enabled": true,
      "completed": false,
      "skipped": false,
      "error": null
    },
    "create_thumbnail": {
      "enabled": false,
      "completed": false,
      "skipped": true,
      "error": null
    }
  },
  "updated": "2026-02-16T00:10:15.456789"
}
```

## Best Practices

### 1. Всегда сохраняйте промежуточные результаты

```python
# ✓ Правильно
result = process_audio(audio_path)
artifacts.save_artifact("cleaned_audio", result)

# ✗ Неправильно (потеря промежуточного файла)
result = process_audio(audio_path)
# Забыли сохранить — при ошибке придется пересчитывать
```

### 2. Используйте метаданные

```python
# Сохранение с контекстом
artifacts.save_artifact(
    "cleaned_audio",
    audio_path,
    metadata={
        "method": "Auphonic API",
        "preset": "podcast",
        "processing_time": 45.2,
        "original_size": 15_000_000,
        "compressed_size": 8_500_000,
    }
)
```

### 3. Проверяйте зависимости между этапами

```python
# Нельзя создать обложку без заголовка
if not workflow.is_step_completed("generate_titles"):
    raise ValueError("Cannot create thumbnail: titles not generated yet")

if not artifacts.has_artifact("selected_title"):
    raise ValueError("No title selected for thumbnail")
```

### 4. Обрабатывайте ошибки правильно

```python
try:
    result = transcribe_audio(audio_path)
    artifacts.save_artifact("raw_transcription", result)
    workflow.mark_completed("transcribe")
except Exception as e:
    workflow.mark_error("transcribe", str(e))
    raise
```

## Testing

Для системы артефактов написаны полные unit-тесты:

```bash
# Запуск тестов
python3 -m unittest tests.test_artifacts -v
```

**Покрытие тестов:**

- ✓ Создание структуры папок
- ✓ Сохранение/получение артефактов
- ✓ Удаление артефактов
- ✓ Persistence манифеста
- ✓ Включение/отключение этапов
- ✓ Отметка завершения/ошибок
- ✓ Получение следующего этапа
- ✓ Сброс workflow
- ✓ Persistence состояния

Все 15 тестов проходят успешно.

## Расширение

### Добавление нового типа артефакта

1. Добавьте тип в `ArtifactsManager.ARTIFACT_TYPES`:

```python
ARTIFACT_TYPES = {
    ...
    "my_new_artifact": "Описание нового артефакта",
}
```

2. Используйте как обычно:

```python
artifacts.save_artifact("my_new_artifact", file_path)
```

### Добавление нового этапа workflow

1. Добавьте этап в `WorkflowState.WORKFLOW_STEPS`:

```python
WORKFLOW_STEPS = [
    ...
    "my_new_step",
]
```

2. Добавьте label в `WorkflowPanel.STEP_LABELS`:

```python
STEP_LABELS = {
    ...
    "my_new_step": "🎯 My New Step",
}
```

3. Реализуйте процессор для этапа в `src/processors/`.

## Future Improvements

- [ ] Версионирование артефактов (хранение нескольких версий)
- [ ] Автоматическое удаление старых артефактов
- [ ] Экспорт/импорт проектов (zip архивы)
- [ ] Детальная статистика по каждому этапу
- [ ] Визуализация зависимостей между этапами
- [ ] Параллельное выполнение независимых этапов
- [ ] Rollback к предыдущим состояниям
- [ ] Cloud storage интеграция (S3, Google Drive)

## Заключение

Artifacts System и Modular Workflow делают Video Studio гибким и надежным инструментом:

- **Не теряете прогресс** — все промежуточные файлы сохранены
- **Экономите время** — пересчитываете только нужные этапы
- **Полный контроль** — включайте только нужные шаги
- **Прозрачность** — видите весь путь обработки видео

Система протестирована, документирована и готова к использованию.
