"""
Тесты для системы артефактов и workflow
"""

import unittest
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.artifacts import ArtifactsManager, WorkflowState


class TestArtifactsManager(unittest.TestCase):
    """Тесты для ArtifactsManager"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        # Создаем временную директорию для тестов
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_output = Path("output")
        
        # Подменяем output на временную папку
        import os
        os.chdir(self.test_dir)
        
        self.artifacts = ArtifactsManager("test_video")
        
    def tearDown(self):
        """Очистка после каждого теста"""
        # Удаляем временную директорию
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_create_folders(self):
        """Проверка создания структуры папок"""
        self.assertTrue(self.artifacts.project_dir.exists())
        self.assertTrue(self.artifacts.folders["video"].exists())
        self.assertTrue(self.artifacts.folders["audio"].exists())
        self.assertTrue(self.artifacts.folders["transcription"].exists())
        self.assertTrue(self.artifacts.folders["titles"].exists())
        self.assertTrue(self.artifacts.folders["thumbnails"].exists())
        self.assertTrue(self.artifacts.folders["metadata"].exists())
        
    def test_sanitize_name(self):
        """Проверка очистки имени проекта"""
        name = "Test Video: 2024 (Final) #1"
        sanitized = self.artifacts._sanitize_name(name)
        # Должны остаться только буквы, цифры и подчеркивания
        self.assertEqual(sanitized, "Test_Video_2024_Final_1")
        
    def test_save_artifact(self):
        """Проверка сохранения артефакта"""
        # Создаем временный файл
        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test video content")
        
        # Сохраняем как артефакт
        saved_path = self.artifacts.save_artifact(
            "original_video",
            test_file,
            metadata={"test_key": "test_value"}
        )
        
        # Проверяем что файл скопирован
        self.assertTrue(saved_path.exists())
        self.assertEqual(saved_path.read_text(), "test video content")
        
        # Проверяем что путь сохранен в манифесте
        self.assertIsNotNone(self.artifacts.artifacts["original_video"])
        
    def test_get_artifact(self):
        """Проверка получения артефакта"""
        # Создаем и сохраняем артефакт
        test_file = self.test_dir / "test.mp3"
        test_file.write_text("test audio")
        self.artifacts.save_artifact("original_audio", test_file)
        
        # Получаем артефакт
        artifact_path = self.artifacts.get_artifact("original_audio")
        self.assertIsNotNone(artifact_path)
        self.assertTrue(artifact_path.exists())
        
        # Проверяем несуществующий артефакт
        missing_artifact = self.artifacts.get_artifact("nonexistent")
        self.assertIsNone(missing_artifact)
        
    def test_has_artifact(self):
        """Проверка наличия артефакта"""
        # До сохранения
        self.assertFalse(self.artifacts.has_artifact("original_video"))
        
        # После сохранения
        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")
        self.artifacts.save_artifact("original_video", test_file)
        
        self.assertTrue(self.artifacts.has_artifact("original_video"))
        
    def test_list_artifacts(self):
        """Проверка списка артефактов"""
        # Создаем несколько артефактов
        for i, artifact_type in enumerate(["original_video", "original_audio"]):
            test_file = self.test_dir / f"test{i}.dat"
            test_file.write_text(f"test {i}")
            self.artifacts.save_artifact(artifact_type, test_file)
            
        # Получаем список
        artifacts_list = self.artifacts.list_artifacts()
        
        self.assertEqual(len(artifacts_list), 2)
        self.assertTrue(any(a["type"] == "original_video" for a in artifacts_list))
        self.assertTrue(any(a["type"] == "original_audio" for a in artifacts_list))
        
    def test_delete_artifact(self):
        """Проверка удаления артефакта"""
        # Создаем артефакт
        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")
        self.artifacts.save_artifact("original_video", test_file)
        
        # Проверяем что есть
        self.assertTrue(self.artifacts.has_artifact("original_video"))
        
        # Удаляем
        result = self.artifacts.delete_artifact("original_video")
        self.assertTrue(result)
        
        # Проверяем что удален
        self.assertFalse(self.artifacts.has_artifact("original_video"))
        
        # Попытка удалить несуществующий
        result = self.artifacts.delete_artifact("nonexistent")
        self.assertFalse(result)
        
    def test_manifest_persistence(self):
        """Проверка сохранения манифеста"""
        # Создаем артефакт
        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")
        self.artifacts.save_artifact("original_video", test_file)
        
        # Проверяем что манифест существует
        self.assertTrue(self.artifacts.manifest_path.exists())
        
        # Загружаем манифест
        import json
        with open(self.artifacts.manifest_path) as f:
            manifest = json.load(f)
            
        self.assertEqual(manifest["project_name"], "test_video")
        self.assertIn("original_video", manifest["artifacts"])


class TestWorkflowState(unittest.TestCase):
    """Тесты для WorkflowState"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.test_dir = Path(tempfile.mkdtemp())
        import os
        os.chdir(self.test_dir)
        
        self.artifacts = ArtifactsManager("test_workflow")
        self.workflow = WorkflowState(self.artifacts)
        
    def tearDown(self):
        """Очистка после каждого теста"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_initial_state(self):
        """Проверка начального состояния"""
        # Все этапы должны быть включены и не завершены
        for step in WorkflowState.WORKFLOW_STEPS:
            self.assertTrue(self.workflow.is_step_enabled(step))
            self.assertFalse(self.workflow.is_step_completed(step))
            
    def test_enable_disable_step(self):
        """Проверка включения/отключения этапов"""
        step = "transcribe"
        
        # Отключаем
        self.workflow.disable_step(step)
        self.assertFalse(self.workflow.is_step_enabled(step))
        self.assertTrue(self.workflow.steps_status[step]["skipped"])
        
        # Включаем обратно
        self.workflow.enable_step(step)
        self.assertTrue(self.workflow.is_step_enabled(step))
        self.assertFalse(self.workflow.steps_status[step]["skipped"])
        
    def test_mark_completed(self):
        """Проверка отметки завершения"""
        step = "import_video"
        
        self.workflow.mark_completed(step)
        self.assertTrue(self.workflow.is_step_completed(step))
        self.assertIsNone(self.workflow.steps_status[step]["error"])
        
    def test_mark_error(self):
        """Проверка отметки ошибки"""
        step = "transcribe"
        error_msg = "API key missing"
        
        self.workflow.mark_error(step, error_msg)
        self.assertEqual(self.workflow.steps_status[step]["error"], error_msg)
        
    def test_get_next_step(self):
        """Проверка получения следующего этапа"""
        # Помечаем первый этап как завершенный
        self.workflow.mark_completed("import_video")
        
        # Следующий должен быть edit_trim
        next_step = self.workflow.get_next_step()
        self.assertEqual(next_step, "edit_trim")
        
        # Отключаем edit_trim
        self.workflow.disable_step("edit_trim")
        
        # Следующий должен быть transcribe
        next_step = self.workflow.get_next_step()
        self.assertEqual(next_step, "transcribe")
        
    def test_reset(self):
        """Проверка сброса workflow"""
        # Завершаем несколько этапов
        self.workflow.mark_completed("import_video")
        self.workflow.mark_completed("edit_trim")
        self.workflow.mark_error("transcribe", "test error")
        
        # Сбрасываем
        self.workflow.reset()
        
        # Все этапы должны быть не завершены и без ошибок
        for step in WorkflowState.WORKFLOW_STEPS:
            self.assertFalse(self.workflow.is_step_completed(step))
            self.assertIsNone(self.workflow.steps_status[step]["error"])
            
    def test_state_persistence(self):
        """Проверка сохранения состояния в файл"""
        # Изменяем состояние
        self.workflow.mark_completed("import_video")
        self.workflow.disable_step("transcribe")
        
        # Проверяем что файл создан
        self.assertTrue(self.workflow.state_file.exists())
        
        # Создаем новый WorkflowState и загружаем состояние
        workflow2 = WorkflowState(self.artifacts)
        
        self.assertTrue(workflow2.is_step_completed("import_video"))
        self.assertFalse(workflow2.is_step_enabled("transcribe"))


if __name__ == "__main__":
    unittest.main()
