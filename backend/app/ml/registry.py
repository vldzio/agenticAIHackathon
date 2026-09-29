"""Loads model artifacts once, verifies their integrity and library versions."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn

from app.config import get_settings
from app.ml import paths

logger = logging.getLogger(__name__)


class ModelLoadError(RuntimeError):
    pass


@dataclass
class LoadedModel:
    name: str
    pipeline: Any
    meta: dict[str, Any]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ModelRegistry:
    def __init__(self, artifact_dir: Path | None = None) -> None:
        self.artifact_dir = artifact_dir or paths.ARTIFACT_DIR
        self._models: dict[str, LoadedModel] = {}
        self._metadata: dict[str, Any] | None = None
        self._lock = threading.Lock()

    @property
    def metadata(self) -> dict[str, Any]:
        if self._metadata is None:
            meta_path = self.artifact_dir / "metadata.json"
            if not meta_path.exists():
                raise ModelLoadError(f"Model metadata not found at {meta_path}. Run `make train`.")
            self._metadata = json.loads(meta_path.read_text())
            self._check_versions(self._metadata.get("environment", {}))
        return self._metadata

    def _check_versions(self, trained_env: dict[str, str]) -> None:
        current = {"scikit_learn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__}
        mismatched = {k: (trained_env.get(k), v) for k, v in current.items() if trained_env.get(k) != v}
        if mismatched:
            message = f"Model artifacts were trained with different library versions (trained, current): {mismatched}"
            if get_settings().strict_model_versions:
                raise ModelLoadError(message + ". Retrain with `make train`.")
            logger.warning(message)

    def get(self, name: str) -> LoadedModel:
        with self._lock:
            if name in self._models:
                return self._models[name]
            meta = self.metadata.get("models", {}).get(name)
            if not meta:
                raise ModelLoadError(f"Model '{name}' is not listed in metadata.json")
            artifact = self.artifact_dir / meta["artifact"]
            if not artifact.exists():
                raise ModelLoadError(f"Model artifact missing: {artifact}")
            if _sha256(artifact) != meta["artifact_sha256"]:
                raise ModelLoadError(f"Integrity check failed for {artifact.name}; refusing to load it.")
            pipeline = joblib.load(artifact)  # integrity-checked above; never load untrusted files
            for calibrated in pipeline.named_steps["clf"].calibrated_classifiers_:
                calibrated.estimator.n_jobs = 1  # tiny single-row predictions: thread-pool spin-up dominates
            loaded = LoadedModel(name=name, pipeline=pipeline, meta=meta)
            self._models[name] = loaded
            logger.info("Loaded model %s", name)
            return loaded

    def warm_up(self) -> None:
        for name in self.metadata.get("models", {}):
            self.get(name)


_registry: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry
