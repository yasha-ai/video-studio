"""
Batch Video Processing Queue

Processes multiple videos through the pipeline sequentially.
Supports transcription, audio cleanup, title generation, and thumbnail creation.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

try:
    from config.settings import Settings
except ImportError:
    Settings = None

from src.processors.whisper_transcriber import WhisperTranscriber
from src.processors.audio_cleanup import AudioCleanup
from src.processors.title_generator import TitleGenerator
from src.processors.cover_generator import CoverGenerator

logger = logging.getLogger(__name__)

# Step name → human-readable label
STEP_LABELS = {
    "transcribe": "Transcription",
    "audio": "Audio Cleanup",
    "titles": "Title Generation",
    "thumbnail": "Thumbnail Generation",
}

DEFAULT_STEPS = ["transcribe", "audio", "titles", "thumbnail"]

# Callback signature: (video_index, total, video_name, step_name, status)
ProgressCallback = Callable[[int, int, str, str, str], None]


class _QueueItem:
    """Internal representation of a queued video."""

    __slots__ = ("video_path", "steps", "status", "error", "completed_steps", "output_dir")

    def __init__(self, video_path: str, steps: list[str], output_dir: Path):
        self.video_path = video_path
        self.steps = list(steps)
        self.status: str = "pending"  # pending | running | done | error
        self.error: Optional[str] = None
        self.completed_steps: list[str] = []
        self.output_dir = output_dir


class BatchProcessor:
    """
    Queue-based batch processor for multiple videos.

    Usage::

        bp = BatchProcessor()
        bp.add_video("/path/to/video1.mp4")
        bp.add_video("/path/to/video2.mp4", steps=["transcribe", "titles"])
        bp.run(progress_callback=my_callback)
        results = bp.get_results()
    """

    def __init__(self):
        self._queue: list[_QueueItem] = []
        self._cancelled = False

        # Shared processor instances
        self._transcriber = WhisperTranscriber()
        self._audio_cleanup = AudioCleanup()
        self._title_generator = TitleGenerator()
        self._cover_generator = CoverGenerator()

        # Batch output root
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if Settings is not None:
            self._batch_dir = Settings.OUTPUT_DIR / f"batch_{timestamp}"
        else:
            self._batch_dir = Path("output") / f"batch_{timestamp}"

    # ── Public API ──────────────────────────────────────────────

    def add_video(self, video_path: str, steps: Optional[list[str]] = None) -> None:
        """
        Add a video to the processing queue.

        Args:
            video_path: Path to the video file.
            steps: Processing steps to run. Defaults to all steps.
        """
        if steps is None:
            steps = list(DEFAULT_STEPS)

        # Validate steps
        for s in steps:
            if s not in STEP_LABELS:
                raise ValueError(
                    f"Unknown step '{s}'. Valid steps: {list(STEP_LABELS.keys())}"
                )

        # Create per-video output directory
        video_name = Path(video_path).stem
        video_output = self._batch_dir / video_name
        video_output.mkdir(parents=True, exist_ok=True)

        self._queue.append(_QueueItem(video_path, steps, video_output))

    def run(self, progress_callback: Optional[ProgressCallback] = None) -> None:
        """
        Process all queued videos sequentially.

        Args:
            progress_callback: ``(video_index, total, video_name, step_name, status)``
        """
        self._cancelled = False
        total = len(self._queue)

        for idx, item in enumerate(self._queue):
            if self._cancelled:
                item.status = "cancelled"
                continue

            video_name = Path(item.video_path).name
            item.status = "running"

            try:
                self._process_video(item, idx, total, video_name, progress_callback)
                if self._cancelled:
                    item.status = "cancelled"
                else:
                    item.status = "done"
            except Exception as exc:
                item.status = "error"
                item.error = str(exc)
                logger.error("Batch: video %s failed: %s", video_name, exc, exc_info=True)
                if progress_callback:
                    progress_callback(idx, total, video_name, "", f"error: {exc}")

    def cancel(self) -> None:
        """Set the cancellation flag. Current step will finish before stopping."""
        self._cancelled = True

    def get_results(self) -> list[dict]:
        """
        Return results for every queued video.

        Returns:
            List of dicts with keys: video_path, status, error, completed_steps.
        """
        return [
            {
                "video_path": item.video_path,
                "status": item.status,
                "error": item.error,
                "completed_steps": list(item.completed_steps),
            }
            for item in self._queue
        ]

    # ── Internal ────────────────────────────────────────────────

    def _process_video(
        self,
        item: _QueueItem,
        idx: int,
        total: int,
        video_name: str,
        cb: Optional[ProgressCallback],
    ) -> None:
        """Run requested steps for a single video."""

        transcription_text: Optional[str] = None
        generated_titles: list[str] = []

        for step in item.steps:
            if self._cancelled:
                return

            step_label = STEP_LABELS.get(step, step)
            if cb:
                cb(idx, total, video_name, step_label, "running")

            try:
                if step == "transcribe":
                    transcription_text = self._run_transcribe(item)
                elif step == "audio":
                    self._run_audio_cleanup(item)
                elif step == "titles":
                    generated_titles = self._run_titles(item, transcription_text)
                elif step == "thumbnail":
                    self._run_thumbnail(item, generated_titles)

                item.completed_steps.append(step)
                if cb:
                    cb(idx, total, video_name, step_label, "done")

            except Exception as exc:
                logger.error(
                    "Batch step '%s' failed for %s: %s", step, video_name, exc, exc_info=True
                )
                if cb:
                    cb(idx, total, video_name, step_label, f"error: {exc}")
                # Continue with next step — don't abort the video

    # ── Step runners ────────────────────────────────────────────

    def _run_transcribe(self, item: _QueueItem) -> Optional[str]:
        output_path = str(item.output_dir / "transcription.txt")
        result = self._transcriber.transcribe(
            video_path=item.video_path,
            output_path=output_path,
        )
        if result and "text" in result:
            return result["text"]
        return None

    def _run_audio_cleanup(self, item: _QueueItem) -> str:
        output_path = str(item.output_dir / "audio_cleaned.wav")
        return self._audio_cleanup.cleanup(
            input_path=item.video_path,
            output_path=output_path,
        )

    def _run_titles(self, item: _QueueItem, transcript: Optional[str]) -> list[str]:
        titles = self._title_generator.generate_titles(
            transcript=transcript,
            count=5,
        )
        # Persist to file
        titles_file = item.output_dir / "titles.txt"
        titles_file.write_text("\n".join(titles), encoding="utf-8")
        return titles

    def _run_thumbnail(self, item: _QueueItem, titles: list[str]) -> list[Path]:
        title = titles[0] if titles else Path(item.video_path).stem
        covers = self._cover_generator.generate_covers(
            title=title,
            count=2,
            output_dir=item.output_dir,
        )
        return covers
