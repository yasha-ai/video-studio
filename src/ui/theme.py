"""
Shared color palette and Russian locale for Video Studio UI.
Import C and L from this module in all UI files.
"""

# ── Color palette (yasha.dev inspired) ──
C = {
    "bg":           "#0d1117",
    "surface":      "#161b22",
    "surface2":     "#1c2128",
    "surface3":     "#2d333b",
    "border":       "#30363d",
    "text":         "#e6edf3",
    "text2":        "#8b949e",
    "text3":        "#484f58",
    "accent":       "#2ea043",
    "accent_hover": "#3fb950",
    "accent_dim":   "#1a3a2a",
    "green":        "#3fb950",
    "green_dim":    "#1a3a2a",
    "red":          "#f85149",
    "orange":       "#d29922",
    "blue":         "#58a6ff",
}

# ── Russian locale ──
L = {
    # App
    "app_title": "Video Studio",
    "app_subtitle": "Видео-пайплайн для YouTube",

    # Sidebar steps
    "step_import": "Импорт",
    "step_assembly": "Сборка",
    "step_transcribe": "Транскрипция",
    "step_audio": "Очистка звука",
    "step_titles": "Заголовки",
    "step_thumbnail": "Обложки",
    "step_preview": "Предпросмотр",
    "step_upload": "Экспорт",

    # Sidebar bottom
    "projects": "Проекты",
    "batch": "Пакетная обработка",
    "settings": "Настройки",
    "help": "Справка",

    # Import panel
    "drop_or_select": "Перетащите или выберите видео",
    "supported_formats": "MP4, MOV, AVI, MKV",
    "select_video": "Выбрать видеофайл",
    "video_loaded": "Видео загружено",
    "choose_another": "Выбрать другой файл",

    # Assembly panel
    "video_assembly": "Сборка видео",
    "assembly_hint": "Выберите интро, аутро и оверлей подписки, затем нажмите Рендер",
    "intro": "Интро",
    "outro": "Аутро",
    "subscribe_overlay": "Оверлей подписки",
    "not_set": "Не выбрано",
    "choose": "Выбрать",
    "clear": "Убрать",
    "overlay_start": "Начало (сек):",
    "position": "Позиция:",
    "render_assembly": "Рендер сборки",
    "play_result": "Воспроизвести результат",
    "add_intro_outro": "Добавьте интро или аутро для сборки",

    # Transcribe panel
    "transcription": "Транскрипция",
    "whisper_local": "Whisper (локально)",
    "gemini_cloud": "Gemini (облако)",
    "start_transcription": "Начать транскрипцию",
    "transcription_result": "Результат транскрипции",
    "transcribing": "Транскрибация...",
    "transcription_in_progress": "Транскрипция выполняется...",
    "wait_for_transcription": "Заголовки и обложки будут сгенерированы на основе транскрипции.\nПожалуйста, подождите.",

    # Audio panel
    "audio_cleanup": "Очистка звука",
    "remove_noise": "Удаление шума и улучшение качества звука",
    "mode": "Режим:",
    "builtin_ffmpeg": "Встроенный (FFmpeg)",
    "auphonic_cloud": "Auphonic (облако)",
    "preset": "Пресет:",
    "clean_audio": "Очистить звук",
    "cleaned_audio_ready": "Звук очищен",
    "play_cleaned": "Воспроизвести очищенный",
    "play_original": "Воспроизвести оригинал",
    "stop": "Стоп",
    "use_cleaned": "Использовать очищенный звук в финальном рендере",

    # Titles panel
    "title_generator": "Генератор заголовков",
    "generate_titles_hint": "Генерация заголовков на основе транскрипции",
    "additional_context": "Дополнительный контекст (необязательно):",
    "generate_titles": "Сгенерировать заголовки",
    "choose_title": "Выберите заголовок",
    "critique_titles": "Оценить все заголовки",

    # Thumbnail panel
    "thumbnail_generator": "Генератор обложек",
    "additional_prompt": "Дополнительный промпт (необязательно):",
    "reference_image": "Референсное изображение:",
    "generate_thumbnails": "Сгенерировать 3 обложки",

    # Preview
    "preview": "Предпросмотр",
    "preview_hint": "Просмотрите видео перед публикацией",
    "play_full": "Воспроизвести видео",
    "quick_preview": "Быстрый просмотр (30с)",
    "open_folder": "Открыть папку",

    # Upload / Export
    "export_upload": "Экспорт / Загрузка",
    "save_locally": "Сохранить локально",
    "export_hint": "Экспортировать все файлы проекта в папку",
    "save_to_folder": "Сохранить в папку...",
    "ai_description": "AI-описание",
    "generate_desc": "Сгенерировать",
    "youtube_upload": "Загрузка на YouTube",

    # Common
    "ready": "Готово",
    "processing": "Обработка...",
    "step_completed": "Шаг завершён",
    "next_step": "Далее >",
    "settings_btn": "Настройки",
    "done": "Готово",
    "error": "Ошибка",
    "cancel": "Отмена",
    "delete": "Удалить",
    "save": "Сохранить",
    "apply": "Применить",
    "save_apply": "Сохранить и применить",
    "copied": "Скопировано!",
    "no_video": "Видео не загружено",
    "select_video_start": "Выберите видео для начала работы",

    # Toasts / notifications
    "transcription_complete": "Транскрипция завершена — генерируем заголовки, обложки и описания...",
    "titles_generated": "Заголовки сгенерированы с критикой!",
    "thumbnails_generated": "Обложки сгенерированы!",
    "descriptions_generated": "Описания сгенерированы!",
    "audio_cleaned": "Звук очищен!",
    "assembly_complete": "Видео собрано! Все шаги выполнены.",
    "settings_applied": "Настройки применены!",
    "project_saved": "Проект сохранён!",
    "project_deleted": "Проект удалён. Готово к новому.",
    "transcription_failed": "Ошибка транскрипции",
    "title_gen_failed": "Ошибка генерации заголовков",
    "thumbnail_gen_failed": "Ошибка генерации обложек",
    "assembly_failed": "Ошибка сборки",
    "audio_cleanup_failed": "Ошибка очистки звука",
    "cleaned_audio_ready": "Звук очищен",
    "transcription_in_progress": "Транскрипция выполняется...",
    "ready_to_transcribe": "Готово к транскрипции",

    # Description panel
    "description_generator": "Генератор описаний",
    "description_hint": "AI генерирует 3 варианта описания на основе транскрипции",
    "generate_descriptions": "Сгенерировать описания",
    "best_description": "Лучшее описание",
    "variant": "Вариант",
    "copy": "Копировать",
    "select": "Выбрать",
    "description_selected": "Описание выбрано!",
}
