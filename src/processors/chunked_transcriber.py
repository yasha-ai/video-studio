"""
Chunked Transcriber — splits audio by silence, transcribes chunks, merges SRT.

Works with any transcription engine (Whisper, Gemini, Parakeet).
Solves: long videos cause quadratic attention complexity, splitting speeds up ~3-5x.

Pipeline:
1. Extract audio from video (WAV 16kHz mono)
2. Detect silence points via ffmpeg silencedetect
3. Split into chunks at silence boundaries (target ~3 min each)
4. Transcribe each chunk independently
5. Merge SRT files with corrected timestamps
6. Cleanup temp files
"""

import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    from config.settings import Settings
except ImportError:
    Settings = None


def _get_ffmpeg() -> str:
    if Settings:
        return Settings.get_ffmpeg()
    import shutil
    return shutil.which("ffmpeg") or "ffmpeg"


def _get_ffprobe() -> str:
    if Settings:
        return Settings.get_ffprobe()
    import shutil
    return shutil.which("ffprobe") or "ffprobe"


def _get_duration(filepath: str) -> float:
    """Get media duration in seconds."""
    cmd = [_get_ffprobe(), "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", filepath]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def _extract_audio(video_path: str, output_wav: str) -> None:
    """Convert video to WAV 16kHz mono for transcription."""
    cmd = [_get_ffmpeg(), "-y", "-i", video_path,
           "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", output_wav]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr[:200]}")
    logger.info(f"Extracted audio: {output_wav}")


def _detect_silence(wav_path: str, min_silence_duration: float = 0.5,
                    noise_threshold: str = "-35dB") -> list[float]:
    """Detect silence points in audio. Returns list of timestamps (seconds)."""
    cmd = [
        _get_ffmpeg(), "-i", wav_path,
        "-af", f"silencedetect=noise={noise_threshold}:d={min_silence_duration}",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    stderr = result.stderr

    # Parse silence_end timestamps
    silence_points = []
    for match in re.finditer(r"silence_end:\s*([\d.]+)", stderr):
        silence_points.append(float(match.group(1)))

    logger.info(f"Detected {len(silence_points)} silence points")
    return silence_points


def _choose_split_points(silence_points: list[float], total_duration: float,
                         target_chunk: float = 180.0, min_chunk: float = 30.0) -> list[float]:
    """Choose optimal split points from silence timestamps.

    Target ~3 min chunks, minimum 30 sec, split at silence boundaries.
    """
    if total_duration <= target_chunk * 1.5:
        return []  # Short enough, no splitting needed

    split_points = []
    last_split = 0.0

    for point in silence_points:
        elapsed = point - last_split
        if elapsed >= target_chunk:
            split_points.append(point)
            last_split = point
        elif elapsed >= target_chunk * 0.7 and (total_duration - point) > min_chunk:
            # Close enough to target and enough remaining
            split_points.append(point)
            last_split = point

    # Remove last split if remaining chunk would be too short
    if split_points and (total_duration - split_points[-1]) < min_chunk:
        split_points.pop()

    logger.info(f"Split points: {split_points} (target {target_chunk}s, total {total_duration:.1f}s)")
    return split_points


def _split_audio(wav_path: str, split_points: list[float],
                 output_dir: Path) -> list[tuple[str, float]]:
    """Split WAV at given points. Returns [(chunk_path, start_offset), ...]."""
    chunks = []
    boundaries = [0.0] + split_points + [_get_duration(wav_path)]

    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        chunk_path = str(output_dir / f"chunk_{i:03d}.wav")

        cmd = [_get_ffmpeg(), "-y",
               "-ss", str(start), "-i", wav_path,
               "-t", str(end - start),
               "-c:a", "copy", chunk_path]
        subprocess.run(cmd, capture_output=True)
        chunks.append((chunk_path, start))
        logger.debug(f"Chunk {i}: {start:.1f}s - {end:.1f}s -> {chunk_path}")

    logger.info(f"Split into {len(chunks)} chunks")
    return chunks


def _shift_srt_timestamps(srt_text: str, offset_seconds: float) -> str:
    """Shift all SRT timestamps by offset_seconds."""
    if offset_seconds == 0:
        return srt_text

    offset_ms = int(offset_seconds * 1000)

    def shift_match(match):
        h, m, s, ms = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
        total_ms = h * 3600000 + m * 60000 + s * 1000 + ms + offset_ms
        if total_ms < 0:
            total_ms = 0
        nh = total_ms // 3600000
        nm = (total_ms % 3600000) // 60000
        ns = (total_ms % 60000) // 1000
        nms = total_ms % 1000
        return f"{nh:02d}:{nm:02d}:{ns:02d},{nms:03d}"

    return re.sub(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", shift_match, srt_text)


def _merge_srt_chunks(chunk_results: list[tuple[str, float]]) -> str:
    """Merge SRT texts from chunks with corrected timestamps.

    Args:
        chunk_results: [(srt_text, start_offset_seconds), ...]

    Returns:
        Merged SRT text with sequential numbering and corrected times.
    """
    merged_lines = []
    subtitle_index = 1

    for srt_text, offset in chunk_results:
        # Shift timestamps
        shifted = _shift_srt_timestamps(srt_text, offset)

        # Re-number subtitles
        for block in re.split(r"\n\n+", shifted.strip()):
            lines = block.strip().split("\n")
            if len(lines) >= 2:
                # Replace subtitle number
                lines[0] = str(subtitle_index)
                merged_lines.append("\n".join(lines))
                subtitle_index += 1

    return "\n\n".join(merged_lines) + "\n"


def transcribe_chunked(
    video_path: str,
    transcribe_fn: Callable[[str], str],
    progress_callback: Optional[Callable[[float, str], None]] = None,
    target_chunk_seconds: float = 180.0,
) -> str:
    """Transcribe video by splitting into chunks at silence boundaries.

    Args:
        video_path: Path to video file.
        transcribe_fn: Function that takes a WAV file path and returns SRT text.
                       Signature: transcribe_fn(wav_path: str) -> str
        progress_callback: Optional callback(percent_0_100, status_message).
        target_chunk_seconds: Target chunk duration (default 3 min).

    Returns:
        Complete SRT text with correct timestamps.
    """
    work_dir = Path(tempfile.mkdtemp(prefix="vs_transcribe_"))
    logger.info(f"Chunked transcription: {video_path}")
    logger.info(f"Work dir: {work_dir}")

    try:
        # Step 1: Extract audio
        if progress_callback:
            progress_callback(5, "Extracting audio...")
        wav_path = str(work_dir / "full_audio.wav")
        _extract_audio(video_path, wav_path)

        total_duration = _get_duration(wav_path)
        logger.info(f"Audio duration: {total_duration:.1f}s")

        # Step 2: Detect silence
        if progress_callback:
            progress_callback(10, "Detecting silence points...")
        silence_points = _detect_silence(wav_path)

        # Step 3: Choose split points
        split_points = _choose_split_points(silence_points, total_duration, target_chunk_seconds)

        if not split_points:
            # Short video or no good split points — transcribe whole thing
            logger.info("No splitting needed, transcribing whole file")
            if progress_callback:
                progress_callback(15, "Transcribing...")
            srt_text = transcribe_fn(wav_path)
            if progress_callback:
                progress_callback(100, "Done")
            return srt_text

        # Step 4: Split audio
        if progress_callback:
            progress_callback(15, f"Splitting into {len(split_points) + 1} chunks...")
        chunks = _split_audio(wav_path, split_points, work_dir)

        # Step 5: Transcribe each chunk
        chunk_results = []
        for i, (chunk_path, offset) in enumerate(chunks):
            pct = 20 + int(70 * i / len(chunks))
            if progress_callback:
                progress_callback(pct, f"Transcribing chunk {i+1}/{len(chunks)}...")

            logger.info(f"Transcribing chunk {i+1}/{len(chunks)} (offset {offset:.1f}s)")
            srt_text = transcribe_fn(chunk_path)
            chunk_results.append((srt_text, offset))

        # Step 6: Merge
        if progress_callback:
            progress_callback(95, "Merging chunks...")
        merged = _merge_srt_chunks(chunk_results)
        logger.info(f"Merged {len(chunk_results)} chunks into final SRT")

        if progress_callback:
            progress_callback(100, "Done")
        return merged

    finally:
        # Cleanup temp files
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)
        logger.debug(f"Cleaned up: {work_dir}")
