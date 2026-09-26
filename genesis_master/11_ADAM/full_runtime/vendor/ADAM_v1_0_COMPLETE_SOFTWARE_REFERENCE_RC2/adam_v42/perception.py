from __future__ import annotations

import ast
import csv
import io
import json
import math
import re
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from adam_v41.universe import AtomicUniverse
from .evidence import AlignedClaim, EvidenceAlignmentEngine


@dataclass(frozen=True)
class PerceptionResult:
    modality: str
    evidence_object_id: str
    claims: tuple[AlignedClaim, ...]
    features: dict[str, Any]
    ambiguity: tuple[dict[str, Any], ...] = ()


class MultimodalPerception:
    """Bounded deterministic perception codecs with mandatory evidence alignment."""

    def __init__(self, universe: AtomicUniverse, *, capability: object | None = None):
        self.alignment = EvidenceAlignmentEngine(universe, capability=capability)

    def _commit(self, payload: bytes, media_type: str, name: str, modality: str, features: dict[str, Any], confidence: float = 1.0,
                ambiguity: tuple[dict[str, Any], ...] = ()) -> PerceptionResult:
        evidence = self.alignment.ingest_evidence(payload, media_type=media_type, name=name)
        claim = self.alignment.assert_claim(
            f"perception::{modality}", features, evidence_object_id=evidence.object_id,
            extractor=f"adam-v0.42-{modality}-codec", confidence=confidence,
            offsets={"bytes": len(payload)}, authoritative=confidence >= 0.5,
        )
        return PerceptionResult(modality, evidence.object_id, (claim,), features, ambiguity)

    def text(self, payload: bytes, name: str = "text.txt") -> PerceptionResult:
        text = payload.decode("utf-8")
        tokens = re.findall(r"[\w'-]+", text, flags=re.UNICODE)
        numbers = [float(x) for x in re.findall(r"(?<!\w)[+-]?(?:\d+\.\d+|\d+)(?!\w)", text)]
        title_candidates = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b", text)
        token_counts: dict[str, int] = {}
        for token in tokens:
            folded = token.casefold()
            token_counts[folded] = token_counts.get(folded, 0) + 1
        token_counts = dict(sorted(token_counts.items(), key=lambda item: (-item[1], item[0]))[:256])
        features = {
            "encoding": "utf-8", "characters": len(text), "tokens": len(tokens),
            "unique_tokens": len(set(t.casefold() for t in tokens)), "numbers": numbers[:100],
            "title_candidates": title_candidates[:50], "token_counts": token_counts,
            "line_count": text.count("\n") + 1,
        }
        ambiguity = ()
        lowered = text.casefold()
        if "bank" in lowered:
            ambiguity = (
                {"sense": "financial_institution", "confidence": 0.5},
                {"sense": "river_edge", "confidence": 0.5},
            )
        return self._commit(payload, "text/plain; charset=utf-8", name, "text", features, 0.98, ambiguity)

    def image(self, payload: bytes, name: str = "image.png") -> PerceptionResult:
        opened = Image.open(io.BytesIO(payload))
        media_type = Image.MIME.get(opened.format, "image/unknown")
        image = opened.convert("RGB")
        arr = np.asarray(image, dtype=np.float32)
        gray = arr.mean(axis=2)
        gx = np.abs(np.diff(gray, axis=1)).mean() if gray.shape[1] > 1 else 0.0
        gy = np.abs(np.diff(gray, axis=0)).mean() if gray.shape[0] > 1 else 0.0
        features = {
            "width": image.width, "height": image.height, "mode": "RGB",
            "mean_rgb": [round(float(x), 6) for x in arr.mean(axis=(0, 1))],
            "std_rgb": [round(float(x), 6) for x in arr.std(axis=(0, 1))],
            "edge_energy": round(float((gx + gy) / 2), 6),
            "aspect_ratio": round(image.width / max(1, image.height), 8),
        }
        return self._commit(payload, media_type, name, "image", features, 0.99)

    def audio(self, payload: bytes, name: str = "audio.wav") -> PerceptionResult:
        with wave.open(io.BytesIO(payload), "rb") as wav:
            channels, rate, width, frames = wav.getnchannels(), wav.getframerate(), wav.getsampwidth(), wav.getnframes()
            raw = wav.readframes(frames)
        dtype = {1: np.uint8, 2: np.int16, 4: np.int32}.get(width)
        if dtype is None:
            raise ValueError("unsupported PCM width")
        samples = np.frombuffer(raw, dtype=dtype).astype(np.float64)
        if width == 1:
            samples = samples - 128.0
        if channels > 1:
            samples = samples.reshape(-1, channels).mean(axis=1)
        peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
        normalized = samples / peak if peak else samples
        rms = math.sqrt(float(np.mean(normalized ** 2))) if len(samples) else 0.0
        zcr = float(np.mean(np.signbit(normalized[1:]) != np.signbit(normalized[:-1]))) if len(samples) > 1 else 0.0
        spectrum = np.abs(np.fft.rfft(normalized[: min(len(normalized), rate * 10)])) if len(samples) else np.array([0.0])
        freqs = np.fft.rfftfreq(max(1, min(len(normalized), rate * 10)), 1 / rate) if len(samples) else np.array([0.0])
        centroid = float((spectrum * freqs).sum() / max(spectrum.sum(), 1e-12))
        features = {
            "channels": channels, "sample_rate": rate, "sample_width": width,
            "frames": frames, "duration_seconds": round(frames / rate, 8),
            "rms": round(rms, 8), "zero_crossing_rate": round(zcr, 8),
            "spectral_centroid_hz": round(centroid, 6),
        }
        return self._commit(payload, "audio/wav", name, "audio", features, 0.99)

    def program(self, payload: bytes, name: str = "program.py") -> PerceptionResult:
        source = payload.decode("utf-8")
        tree = ast.parse(source)
        node_counts: dict[str, int] = {}
        imports, functions, classes = [], [], []
        for node in ast.walk(tree):
            node_counts[type(node).__name__] = node_counts.get(type(node).__name__, 0) + 1
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
        features = {
            "language": "python", "ast_nodes": sum(node_counts.values()), "node_counts": node_counts,
            "imports": sorted(set(imports)), "functions": functions, "classes": classes,
            "branch_points": sum(node_counts.get(x, 0) for x in ("If", "For", "While", "Try", "Match")),
        }
        return self._commit(payload, "text/x-python", name, "program", features, 1.0)

    def tabular_csv(self, payload: bytes, name: str = "table.csv") -> PerceptionResult:
        text = payload.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        width = max((len(r) for r in rows), default=0)
        headers = rows[0] if rows else []
        numeric = 0
        nonempty = 0
        for row in rows[1:]:
            for value in row:
                if value != "":
                    nonempty += 1
                    try:
                        float(value); numeric += 1
                    except ValueError:
                        pass
        features = {
            "rows": len(rows), "columns": width, "headers": headers,
            "nonempty_cells": nonempty, "numeric_fraction": round(numeric / max(1, nonempty), 8),
        }
        return self._commit(payload, "text/csv", name, "tabular", features, 1.0)
