# Settings UI

**Status:** ✅ Implemented  
**Created:** 2026-02-16  
**Location:** `src/ui/settings_panel.py`

## Описание

Settings UI — панель настроек приложения Video Studio для управления:
- API ключами (Gemini, OpenAI, Auphonic, YouTube)
- Настройками Whisper (модель, устройство)
- Путями проекта

## Архитектура

### Класс `SettingsPanel`

Наследует `ctk.CTkFrame` (CustomTkinter).

**Основные компоненты:**

1. **Entry Fields** (поля ввода)
   - API ключи с маскировкой (`show="*"`)
   - YouTube Client ID/Secret
   
2. **Dropdown Menus** (выпадающие списки)
   - Whisper Model: `tiny`, `base`, `small`, `medium`, `large`
   - Whisper Device: `cpu`, `cuda`

3. **Buttons**
   - `Save Settings` — сохранение в `.env`
   - `Reload` — перезагрузка из `.env`

4. **Status Label** — индикатор статуса операций

## Функционал

### Загрузка настроек

```python
def _load_settings(self):
    """Загрузка настроек из .env файла"""
```

- Читает `.env` файл
- Парсит `KEY=VALUE` формат
- Заполняет UI поля текущими значениями
- Игнорирует комментарии и пустые строки

### Сохранение настроек

```python
def _save_settings(self):
    """Сохранение настроек в .env файл"""
```

- Собирает значения из всех полей UI
- Обновляет существующие записи в `.env`
- Добавляет новые ключи в конец файла
- Сохраняет комментарии из оригинального `.env`
- Обновляет `os.environ` для текущей сессии

### Callback API

```python
settings_panel = SettingsPanel(
    parent,
    on_save=lambda settings: print(settings)
)
```

Вызывается после успешного сохранения с dict всех настроек.

## Безопасность

- **Маскировка API ключей:** Все поля с `KEY` или `SECRET` в названии используют `show="*"`
- **Валидация:** Сохраняются только непустые значения
- **Обновление окружения:** После сохранения обновляется `os.environ` для немедленного применения

## Интеграция

### Импорт

```python
from ui.settings_panel import SettingsPanel
```

### Использование в главном окне

```python
# В main_window.py или main_window_v2.py:
settings_panel = SettingsPanel(
    parent=self,
    on_save=self._on_settings_saved
)
settings_panel.pack(fill="both", expand=True)
```

### Тестирование

Запустите тестовое окно:

```bash
cd ~/clawd/video-studio
python tests/test_settings_panel.py
```

## UI Layout

```
┌─────────────────────────────────────────┐
│ ⚙️ Settings                             │
├─────────────────────────────────────────┤
│                                         │
│ 🔑 API Keys                            │
│ ─────────────────────────────────────  │
│ Google Gemini API Key  [***********]   │
│ OpenAI API Key         [***********]   │
│ Auphonic API Key       [***********]   │
│                                         │
│ 📺 YouTube Settings                    │
│ ─────────────────────────────────────  │
│ YouTube Client ID      [input field]   │
│ YouTube Client Secret  [***********]   │
│                                         │
│ 🎤 Whisper Settings                    │
│ ─────────────────────────────────────  │
│ Whisper Model          [base ▼]        │
│ Whisper Device         [cpu ▼]         │
│                                         │
├─────────────────────────────────────────┤
│ [💾 Save Settings]         [🔄 Reload] │
│           ✓ Settings saved              │
└─────────────────────────────────────────┘
```

## Зависимости

- `customtkinter` — UI framework
- `python-dotenv` — для загрузки `.env` (используется в `config/settings.py`)

## TODO

- [ ] Валидация API ключей (проверка формата)
- [ ] Тест подключения к API (кнопка "Test Connection")
- [ ] Экспорт/импорт настроек (JSON)
- [ ] Темная/светлая тема (если нужно)

## Примечания

- Файл `.env` должен находиться в корне проекта: `~/clawd/video-studio/.env`
- Если `.env` отсутствует, панель покажет предупреждение: `⚠️ .env file not found`
- Комментарии в `.env` сохраняются при перезаписи файла
