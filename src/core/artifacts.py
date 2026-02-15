"""
Artifacts System — управление промежуточными файлами проекта
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import json


class ArtifactsManager:
    """Менеджер артефактов проекта"""
    
    # Типы артефактов
    ARTIFACT_TYPES = {
        "original_video": "Исходное видео",
        "intro_video": "Интро",
        "outro_video": "Аутро",
        "merged_video": "Склеенное видео",
        "video_no_audio": "Видео без звука",
        "original_audio": "Исходный звук",
        "cleaned_audio": "Очищенный звук (AI)",
        "auphonic_audio": "Обработанный звук (Auphonic)",
        "final_audio": "Финальный звук",
        "raw_transcription": "Сырая транскрипция",
        "fixed_transcription": "Исправленная транскрипция",
        "timecodes": "Таймкоды",
        "key_moments": "Ключевые моменты",
        "titles_list": "Список заголовков",
        "titles_critique": "Критика заголовков",
        "selected_title": "Выбранный заголовок",
        "thumbnail_1": "Обложка 1",
        "thumbnail_2": "Обложка 2",
        "thumbnail_3": "Обложка 3",
        "thumbnail_4": "Обложка 4",
        "selected_thumbnail": "Выбранная обложка",
        "final_video": "Финальное видео для загрузки",
        "youtube_metadata": "Метаданные YouTube",
    }
    
    def __init__(self, project_name: str):
        """
        Инициализация менеджера артефактов
        
        Args:
            project_name: Имя проекта (название видео или уникальный ID)
        """
        self.project_name = self._sanitize_name(project_name)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.project_id = f"{self.project_name}_{self.timestamp}"
        
        # Корневая папка для всех артефактов
        self.artifacts_root = Path("output/artifacts")
        
        # Папка текущего проекта
        self.project_dir = self.artifacts_root / self.project_id
        
        # Структура папок для артефактов
        self.folders = {
            "video": self.project_dir / "video",
            "audio": self.project_dir / "audio",
            "transcription": self.project_dir / "transcription",
            "titles": self.project_dir / "titles",
            "thumbnails": self.project_dir / "thumbnails",
            "metadata": self.project_dir / "metadata",
        }
        
        # Манифест проекта (JSON с метаданными всех артефактов)
        self.manifest_path = self.project_dir / "manifest.json"
        
        # Текущее состояние артефактов
        self.artifacts: Dict[str, Optional[str]] = {
            artifact_type: None for artifact_type in self.ARTIFACT_TYPES
        }
        
        # Создаем структуру папок
        self._create_folders()
        
    def _sanitize_name(self, name: str) -> str:
        """Очистка имени проекта от недопустимых символов"""
        # Убираем спецсимволы, оставляем только буквы, цифры, дефис и подчеркивание
        import re
        sanitized = re.sub(r'[^\w\s-]', '', name)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        return sanitized[:50]  # Ограничение длины
        
    def _create_folders(self):
        """Создание структуры папок для артефактов"""
        for folder in self.folders.values():
            folder.mkdir(parents=True, exist_ok=True)
            
    def save_artifact(
        self, 
        artifact_type: str, 
        file_path: Path, 
        metadata: Optional[Dict] = None
    ) -> Path:
        """
        Сохранение артефакта в систему
        
        Args:
            artifact_type: Тип артефакта (из ARTIFACT_TYPES)
            file_path: Путь к исходному файлу
            metadata: Дополнительные метаданные (опционально)
            
        Returns:
            Путь к сохраненному артефакту
        """
        if artifact_type not in self.ARTIFACT_TYPES:
            raise ValueError(f"Unknown artifact type: {artifact_type}")
        
        # Определяем папку назначения
        destination_folder = self._get_folder_for_artifact(artifact_type)
        
        # Копируем файл в папку артефактов
        file_suffix = file_path.suffix
        destination_path = destination_folder / f"{artifact_type}{file_suffix}"
        
        # Копирование файла
        import shutil
        shutil.copy2(file_path, destination_path)
        
        # Сохраняем путь в манифесте
        self.artifacts[artifact_type] = str(destination_path)
        
        # Сохраняем метаданные если есть
        if metadata:
            self._save_metadata(artifact_type, metadata)
        
        # Обновляем манифест
        self._update_manifest()
        
        return destination_path
        
    def get_artifact(self, artifact_type: str) -> Optional[Path]:
        """
        Получить путь к артефакту
        
        Args:
            artifact_type: Тип артефакта
            
        Returns:
            Путь к файлу или None если артефакт не существует
        """
        artifact_path = self.artifacts.get(artifact_type)
        if artifact_path and Path(artifact_path).exists():
            return Path(artifact_path)
        return None
        
    def has_artifact(self, artifact_type: str) -> bool:
        """Проверка наличия артефакта"""
        return self.get_artifact(artifact_type) is not None
        
    def list_artifacts(self) -> List[Dict]:
        """
        Список всех артефактов проекта
        
        Returns:
            Список словарей с информацией об артефактах
        """
        artifacts_list = []
        for artifact_type, artifact_path in self.artifacts.items():
            if artifact_path and Path(artifact_path).exists():
                path_obj = Path(artifact_path)
                artifacts_list.append({
                    "type": artifact_type,
                    "name": self.ARTIFACT_TYPES[artifact_type],
                    "path": str(path_obj),
                    "size": path_obj.stat().st_size,
                    "created": datetime.fromtimestamp(
                        path_obj.stat().st_ctime
                    ).isoformat(),
                })
        return artifacts_list
        
    def delete_artifact(self, artifact_type: str) -> bool:
        """
        Удаление артефакта
        
        Args:
            artifact_type: Тип артефакта
            
        Returns:
            True если удален, False если не существовал
        """
        artifact_path = self.get_artifact(artifact_type)
        if artifact_path:
            artifact_path.unlink()
            self.artifacts[artifact_type] = None
            self._update_manifest()
            return True
        return False
        
    def _get_folder_for_artifact(self, artifact_type: str) -> Path:
        """Определение папки для типа артефакта"""
        if "video" in artifact_type:
            return self.folders["video"]
        elif "audio" in artifact_type:
            return self.folders["audio"]
        elif "transcription" in artifact_type or "timecodes" in artifact_type:
            return self.folders["transcription"]
        elif "title" in artifact_type:
            return self.folders["titles"]
        elif "thumbnail" in artifact_type:
            return self.folders["thumbnails"]
        else:
            return self.folders["metadata"]
            
    def _save_metadata(self, artifact_type: str, metadata: Dict):
        """Сохранение метаданных артефакта"""
        metadata_path = self.folders["metadata"] / f"{artifact_type}_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
    def _update_manifest(self):
        """Обновление манифеста проекта"""
        manifest_data = {
            "project_name": self.project_name,
            "project_id": self.project_id,
            "created": self.timestamp,
            "updated": datetime.now().isoformat(),
            "artifacts": self.artifacts,
        }
        
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            
    def export_summary(self) -> str:
        """
        Экспорт краткой сводки по проекту
        
        Returns:
            Текстовая сводка с информацией о всех артефактах
        """
        summary_lines = [
            f"Project: {self.project_name}",
            f"ID: {self.project_id}",
            f"Location: {self.project_dir}",
            "",
            "Artifacts:",
        ]
        
        artifacts = self.list_artifacts()
        if not artifacts:
            summary_lines.append("  (no artifacts yet)")
        else:
            for artifact in artifacts:
                size_mb = artifact['size'] / (1024 * 1024)
                summary_lines.append(
                    f"  ✓ {artifact['name']}: {size_mb:.2f} MB"
                )
        
        return "\n".join(summary_lines)


class WorkflowState:
    """Состояние workflow (какие этапы выполнены)"""
    
    # Все возможные этапы workflow
    WORKFLOW_STEPS = [
        "import_video",       # Импорт видео
        "edit_trim",         # Редактирование и обрезка
        "transcribe",        # Транскрибация
        "clean_audio",       # Очистка аудио
        "generate_titles",   # Генерация заголовков
        "create_thumbnail",  # Создание обложки
        "preview",           # Предпросмотр
        "upload_youtube",    # Загрузка на YouTube
    ]
    
    def __init__(self, artifacts_manager: ArtifactsManager):
        """
        Инициализация состояния workflow
        
        Args:
            artifacts_manager: Менеджер артефактов для проекта
        """
        self.artifacts = artifacts_manager
        self.state_file = artifacts_manager.project_dir / "workflow_state.json"
        
        # Состояние каждого этапа
        self.steps_status = {
            step: {
                "enabled": True,      # Включен ли этап
                "completed": False,   # Завершен ли этап
                "skipped": False,     # Пропущен ли этап
                "error": None,        # Ошибка при выполнении
            } for step in self.WORKFLOW_STEPS
        }
        
        # Загружаем состояние если файл существует
        self._load_state()
        
    def enable_step(self, step: str):
        """Включить этап"""
        if step in self.steps_status:
            self.steps_status[step]["enabled"] = True
            self.steps_status[step]["skipped"] = False
            self._save_state()
            
    def disable_step(self, step: str):
        """Отключить этап (будет пропущен)"""
        if step in self.steps_status:
            self.steps_status[step]["enabled"] = False
            self.steps_status[step]["skipped"] = True
            self._save_state()
            
    def mark_completed(self, step: str):
        """Отметить этап как завершенный"""
        if step in self.steps_status:
            self.steps_status[step]["completed"] = True
            self.steps_status[step]["error"] = None
            self._save_state()
            
    def mark_error(self, step: str, error_message: str):
        """Отметить ошибку на этапе"""
        if step in self.steps_status:
            self.steps_status[step]["error"] = error_message
            self._save_state()
            
    def is_step_enabled(self, step: str) -> bool:
        """Проверка включен ли этап"""
        return self.steps_status.get(step, {}).get("enabled", False)
        
    def is_step_completed(self, step: str) -> bool:
        """Проверка завершен ли этап"""
        return self.steps_status.get(step, {}).get("completed", False)
        
    def get_next_step(self) -> Optional[str]:
        """Получить следующий незавершенный этап"""
        for step in self.WORKFLOW_STEPS:
            if (self.is_step_enabled(step) and 
                not self.is_step_completed(step)):
                return step
        return None
        
    def reset(self):
        """Сброс всех этапов"""
        for step in self.steps_status:
            self.steps_status[step]["completed"] = False
            self.steps_status[step]["error"] = None
        self._save_state()
        
    def _save_state(self):
        """Сохранение состояния в файл"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump({
                "steps": self.steps_status,
                "updated": datetime.now().isoformat(),
            }, f, indent=2, ensure_ascii=False)
            
    def _load_state(self):
        """Загрузка состояния из файла"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "steps" in data:
                    self.steps_status.update(data["steps"])
                    
    def get_summary(self) -> str:
        """Сводка по статусу workflow"""
        completed = sum(
            1 for s in self.steps_status.values() if s["completed"]
        )
        enabled = sum(
            1 for s in self.steps_status.values() if s["enabled"]
        )
        
        lines = [
            f"Workflow Progress: {completed}/{enabled} steps completed",
            "",
        ]
        
        for step in self.WORKFLOW_STEPS:
            status = self.steps_status[step]
            
            if not status["enabled"]:
                icon = "⊗"
                text = "Disabled"
            elif status["completed"]:
                icon = "✓"
                text = "Completed"
            elif status["error"]:
                icon = "✗"
                text = f"Error: {status['error']}"
            else:
                icon = "○"
                text = "Pending"
                
            step_name = step.replace("_", " ").title()
            lines.append(f"  {icon} {step_name}: {text}")
            
        return "\n".join(lines)
