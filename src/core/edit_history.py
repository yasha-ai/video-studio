"""
Non-destructive edit history system.

The original video file is NEVER modified. All editing operations are stored
as JSON and applied in sequence during final render via ffmpeg.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Supported operation types.
OPERATION_TYPES = frozenset({
    "trim",
    "concat_intro",
    "concat_outro",
    "overlay_subscribe",
})


class EditHistory:
    """Stores a stack of editing operations with undo/redo support.

    Operations are plain dicts validated against known schemas.
    The original video path is kept for reference but never modified.
    """

    def __init__(self, original_video: str | Path) -> None:
        self.original_video = str(original_video)
        self._operations: list[dict[str, Any]] = []
        self._redo_stack: list[dict[str, Any]] = []
        self._created = datetime.now(timezone.utc).isoformat()
        self._updated = self._created

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, operation: dict[str, Any]) -> None:
        """Append an operation and clear the redo stack."""
        self._validate(operation)
        operation = deepcopy(operation)
        operation["_added_at"] = datetime.now(timezone.utc).isoformat()
        self._operations.append(operation)
        self._redo_stack.clear()
        self._touch()

    def undo(self) -> dict[str, Any] | None:
        """Pop the last operation onto the redo stack and return it."""
        if not self._operations:
            return None
        op = self._operations.pop()
        self._redo_stack.append(op)
        self._touch()
        return op

    def redo(self) -> dict[str, Any] | None:
        """Re-apply the last undone operation."""
        if not self._redo_stack:
            return None
        op = self._redo_stack.pop()
        self._operations.append(op)
        self._touch()
        return op

    def clear(self) -> None:
        """Remove all operations and redo history."""
        self._operations.clear()
        self._redo_stack.clear()
        self._touch()

    def get_operations(self) -> list[dict[str, Any]]:
        """Return a copy of the current operation list (without internal keys)."""
        return [self._strip_internal(op) for op in self._operations]

    @property
    def can_undo(self) -> bool:
        return len(self._operations) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        """Serialize history to a JSON file."""
        data = {
            "original_video": self.original_video,
            "operations": self.get_operations(),
            "created": self._created,
            "updated": self._updated,
        }
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> EditHistory:
        """Load history from a JSON file and return a new instance."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        instance = cls(data["original_video"])
        instance._created = data.get("created", instance._created)
        instance._updated = data.get("updated", instance._updated)
        for op in data.get("operations", []):
            instance.add(op)
        return instance

    # ------------------------------------------------------------------
    # FFmpeg command builder
    # ------------------------------------------------------------------

    @staticmethod
    def build_ffmpeg_args(
        operations: list[dict[str, Any]],
        input_path: str | Path,
        output_path: str | Path,
    ) -> list[str]:
        """Convert an operation list into ffmpeg CLI arguments.

        Strategy:
        - Single trim with no other ops -> fast stream-copy with -ss / -t.
        - Anything more complex -> filter_complex pipeline.
        """
        input_path = str(input_path)
        output_path = str(output_path)

        if not operations:
            # No edits: simple copy.
            return ["ffmpeg", "-y", "-i", input_path, "-c", "copy", output_path]

        # Classify operations.
        trims = [op for op in operations if op["type"] == "trim"]
        intros = [op for op in operations if op["type"] == "concat_intro"]
        outros = [op for op in operations if op["type"] == "concat_outro"]
        overlays = [op for op in operations if op["type"] == "overlay_subscribe"]

        is_simple_trim = len(trims) == 1 and not intros and not outros and not overlays

        if is_simple_trim:
            return _build_simple_trim(trims[0], input_path, output_path)

        return _build_complex(
            trims=trims,
            intros=intros,
            outros=outros,
            overlays=overlays,
            input_path=input_path,
            output_path=output_path,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(operation: dict[str, Any]) -> None:
        op_type = operation.get("type")
        if op_type not in OPERATION_TYPES:
            raise ValueError(
                f"Unknown operation type '{op_type}'. "
                f"Supported: {', '.join(sorted(OPERATION_TYPES))}"
            )

        if op_type == "trim":
            if "start" not in operation or "end" not in operation:
                raise ValueError("trim requires 'start' and 'end' (seconds)")
            if float(operation["start"]) >= float(operation["end"]):
                raise ValueError("trim 'start' must be less than 'end'")

        elif op_type in ("concat_intro", "concat_outro"):
            if "path" not in operation:
                raise ValueError(f"{op_type} requires 'path'")

        elif op_type == "overlay_subscribe":
            if "path" not in operation:
                raise ValueError("overlay_subscribe requires 'path'")

    @staticmethod
    def _strip_internal(op: dict[str, Any]) -> dict[str, Any]:
        """Return a copy without internal keys (prefixed with '_')."""
        return {k: v for k, v in op.items() if not k.startswith("_")}

    def _touch(self) -> None:
        self._updated = datetime.now(timezone.utc).isoformat()

    def __repr__(self) -> str:
        return (
            f"EditHistory(original={self.original_video!r}, "
            f"ops={len(self._operations)}, redo={len(self._redo_stack)})"
        )


# ======================================================================
# FFmpeg argument builders (module-private)
# ======================================================================


def _build_simple_trim(
    trim: dict[str, Any], input_path: str, output_path: str
) -> list[str]:
    """Fast trim using stream copy (no re-encoding)."""
    start = float(trim["start"])
    duration = float(trim["end"]) - start
    return [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-i", input_path,
        "-t", f"{duration:.3f}",
        "-c", "copy",
        output_path,
    ]


def _build_complex(
    *,
    trims: list[dict[str, Any]],
    intros: list[dict[str, Any]],
    outros: list[dict[str, Any]],
    overlays: list[dict[str, Any]],
    input_path: str,
    output_path: str,
) -> list[str]:
    """Build a filter_complex pipeline for multi-operation edits."""
    args: list[str] = ["ffmpeg", "-y"]
    inputs: list[str] = []  # tracks input indices
    filter_parts: list[str] = []

    # --- Input 0: main video -----------------------------------------
    if trims:
        # Use the first trim for seek (others are ignored for now).
        trim = trims[0]
        args += ["-ss", f"{float(trim['start']):.3f}"]
        args += ["-to", f"{float(trim['end']):.3f}"]
    args += ["-i", input_path]
    inputs.append(input_path)
    main_idx = 0

    # --- Intro inputs -------------------------------------------------
    intro_indices: list[int] = []
    for intro in intros:
        args += ["-i", intro["path"]]
        inputs.append(intro["path"])
        intro_indices.append(len(inputs) - 1)

    # --- Outro inputs -------------------------------------------------
    outro_indices: list[int] = []
    for outro in outros:
        args += ["-i", outro["path"]]
        inputs.append(outro["path"])
        outro_indices.append(len(inputs) - 1)

    # --- Overlay inputs -----------------------------------------------
    overlay_indices: list[int] = []
    for ov in overlays:
        args += ["-i", ov["path"]]
        inputs.append(ov["path"])
        overlay_indices.append(len(inputs) - 1)

    # --- Build filter_complex graph -----------------------------------
    # Scale all concat segments to the same resolution.
    segments: list[str] = []  # filter labels for concat

    # Intros first.
    for idx in intro_indices:
        label = f"intro{idx}"
        filter_parts.append(
            f"[{idx}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[{label}v]"
        )
        filter_parts.append(f"[{idx}:a]aresample=48000[{label}a]")
        segments.append(f"[{label}v][{label}a]")

    # Main video.
    main_label = "main"
    filter_parts.append(
        f"[{main_idx}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[{main_label}v]"
    )
    filter_parts.append(f"[{main_idx}:a]aresample=48000[{main_label}a]")
    segments.append(f"[{main_label}v][{main_label}a]")

    # Outros last.
    for idx in outro_indices:
        label = f"outro{idx}"
        filter_parts.append(
            f"[{idx}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[{label}v]"
        )
        filter_parts.append(f"[{idx}:a]aresample=48000[{label}a]")
        segments.append(f"[{label}v][{label}a]")

    # Concatenation.
    n_segments = len(segments)
    concat_input = "".join(segments)
    current_v = "concatv"
    current_a = "concata"
    filter_parts.append(
        f"{concat_input}concat=n={n_segments}:v=1:a=1[{current_v}][{current_a}]"
    )

    # Overlays (applied on top of concatenated output).
    for i, ov in enumerate(overlays):
        ov_idx = overlay_indices[i]
        ov_label = f"ov{ov_idx}"

        # Chromakey + scale the overlay.
        chroma = ov.get("chromakey_color", "0x00FF00")
        scale = float(ov.get("scale", 0.2))
        w = int(1920 * scale)
        h = int(1080 * scale)
        filter_parts.append(
            f"[{ov_idx}:v]chromakey={chroma}:0.1:0.2,"
            f"scale={w}:{h}[{ov_label}]"
        )

        # Position mapping.
        position = ov.get("position", "bottom-right")
        x, y = _position_to_xy(position, w, h)
        start_time = float(ov.get("start_time", 0))
        next_v = f"outv{i}"
        filter_parts.append(
            f"[{current_v}][{ov_label}]overlay={x}:{y}:"
            f"enable='gte(t,{start_time:.1f})'[{next_v}]"
        )
        current_v = next_v

    # Final mapping.
    filter_complex = ";\n".join(filter_parts)
    args += ["-filter_complex", filter_complex]
    args += ["-map", f"[{current_v}]", "-map", f"[{current_a}]"]
    args += ["-c:v", "libx264", "-preset", "fast", "-crf", "18"]
    args += ["-c:a", "aac", "-b:a", "192k"]
    args += [output_path]

    return args


def _position_to_xy(position: str, w: int, h: int) -> tuple[str, str]:
    """Map a named position to ffmpeg overlay x:y expressions."""
    margin = 20
    positions = {
        "top-left": (str(margin), str(margin)),
        "top-right": (f"W-{w}-{margin}", str(margin)),
        "bottom-left": (str(margin), f"H-{h}-{margin}"),
        "bottom-right": (f"W-{w}-{margin}", f"H-{h}-{margin}"),
        "center": (f"(W-{w})/2", f"(H-{h})/2"),
    }
    return positions.get(position, positions["bottom-right"])
