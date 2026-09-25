"""Loader and validator for pipeline JSON manifests."""

import json
from pathlib import Path
from typing import Any

from viper.engine.models import PipelineManifest
from viper.engine.orchestrator import Orchestrator

DEFAULT_PIPELINES_DIR = Path(__file__).resolve().parent.parent / 'pipelines'


def load_manifest(path: Path | str) -> PipelineManifest:
    """Read, parse, validate, and cycle-check a single pipeline manifest."""
    file_path = Path(path)
    raw_content = file_path.read_text(encoding='utf-8')
    data: dict[str, Any] = json.loads(raw_content)

    manifest = PipelineManifest.model_validate(data)

    # Validate DAG integrity and cycle detection
    deps = {
        stage.id: Orchestrator._extract_dependencies(stage)
        for stage in manifest.stages
    }
    Orchestrator._detect_cycles(manifest.stages, deps)

    return manifest


def load_manifests_from_dir(
    directory: Path | str | None = None,
) -> dict[str, PipelineManifest]:
    """Load and validate all JSON manifests in the specified directory."""
    target_dir = Path(directory) if directory else DEFAULT_PIPELINES_DIR
    manifests: dict[str, PipelineManifest] = {}

    if not target_dir.exists() or not target_dir.is_dir():
        return manifests

    for json_path in sorted(target_dir.glob('*.json')):
        manifest = load_manifest(json_path)
        manifests[manifest.id] = manifest

    return manifests


class ManifestLoader:
    """Registry maintaining loaded pipeline manifests in memory."""

    def __init__(self, pipelines_dir: Path | str | None = None) -> None:
        self.pipelines_dir = (
            Path(pipelines_dir) if pipelines_dir else DEFAULT_PIPELINES_DIR
        )
        self._manifests: dict[str, PipelineManifest] = {}

    def load_all(self) -> dict[str, PipelineManifest]:
        """(Re)load all manifests from disk."""
        self._manifests = load_manifests_from_dir(self.pipelines_dir)
        return self._manifests

    def get(self, manifest_id: str) -> PipelineManifest | None:
        """Retrieve a pipeline manifest by ID, loading if cache is empty."""
        if not self._manifests:
            self.load_all()
        return self._manifests.get(manifest_id)


_global_loader = ManifestLoader()


def get_manifest(manifest_id: str) -> PipelineManifest | None:
    """Retrieve a cached pipeline manifest by ID from global loader."""
    return _global_loader.get(manifest_id)
