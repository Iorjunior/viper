"""Unit tests for pipeline manifests and manifest loader."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import viper.stages  # noqa: F401
from viper.engine.manifest_loader import (
    ManifestLoader,
    get_manifest,
    load_manifest,
    load_manifests_from_dir,
)
from viper.engine.models import PipelineManifest, PipelineStageConfig
from viper.engine.registry import global_registry


def test_pipeline_stage_config_params_fallback() -> None:
    """Ensure PipelineStageConfig supports params as an alias for inputs."""
    cfg = PipelineStageConfig(
        id='step1',
        stage='extract_audio',
        params={'video': 'test.mp4'},
    )
    assert cfg.inputs == {'video': 'test.mp4'}


def test_load_manifest_single(tmp_path: Path) -> None:
    """Test loading a single valid manifest file."""
    manifest_data = {
        'id': 'test_pipeline',
        'name': 'Test Pipeline',
        'description': 'A simple pipeline test',
        'icon': 'test',
        'tags': ['test'],
        'builtin': False,
        'inputs': {'url': {'type': 'string', 'label': 'URL'}},
        'stages': [
            {
                'id': 'download',
                'stage': 'download_video',
                'params': {'source': '{{ inputs.url }}'},
            }
        ],
        'outputs': {'video': '{{ stages.download.output }}'},
    }
    file_path = tmp_path / 'test.json'
    file_path.write_text(json.dumps(manifest_data), encoding='utf-8')

    manifest = load_manifest(file_path)
    assert isinstance(manifest, PipelineManifest)
    assert manifest.id == 'test_pipeline'
    assert len(manifest.stages) == 1
    assert manifest.stages[0].stage == 'download_video'
    assert manifest.stages[0].inputs == {'source': '{{ inputs.url }}'}


def test_load_manifest_invalid_json(tmp_path: Path) -> None:
    """Test error handling when manifest contains invalid JSON."""
    file_path = tmp_path / 'broken.json'
    file_path.write_text('{broken json', encoding='utf-8')

    with pytest.raises(json.JSONDecodeError):
        load_manifest(file_path)


def test_load_manifest_validation_error(tmp_path: Path) -> None:
    """Test error handling when manifest schema is invalid."""
    file_path = tmp_path / 'invalid.json'
    file_path.write_text(
        json.dumps({'invalid': 'missing id and name'}),
        encoding='utf-8',
    )

    with pytest.raises(ValidationError):
        load_manifest(file_path)


def test_load_manifest_cycle_detection(tmp_path: Path) -> None:
    """Test that manifest loader detects cyclic dependencies in stages."""
    manifest_data = {
        'id': 'cyclic_pipe',
        'name': 'Cyclic Pipe',
        'stages': [
            {
                'id': 'stage_a',
                'stage': 'download_video',
                'inputs': {'x': '{{ stages.stage_b.output }}'},
            },
            {
                'id': 'stage_b',
                'stage': 'extract_audio',
                'inputs': {'y': '{{ stages.stage_a.output }}'},
            },
        ],
    }
    file_path = tmp_path / 'cyclic.json'
    file_path.write_text(json.dumps(manifest_data), encoding='utf-8')

    with pytest.raises(ValueError, match=r'(?i)cycle'):
        load_manifest(file_path)


def test_load_manifests_non_existent_dir(tmp_path: Path) -> None:
    """Test loading manifests from missing directory returns empty dict."""
    assert load_manifests_from_dir(tmp_path / 'does_not_exist') == {}


def test_builtin_manifests_loading() -> None:
    """Ensure all builtin manifests load successfully from directory."""
    manifests = load_manifests_from_dir()
    expected_ids = {
        'convert_video',
        'download_video',
        'extract_audio',
        'full_dubbing',
        'separate_vocals',
        'transcribe_translate',
    }
    assert expected_ids.issubset(set(manifests.keys()))


def test_all_builtin_manifests_are_valid() -> None:
    """Validate all builtin manifests refer to registered stages."""
    manifests = load_manifests_from_dir()
    for manifest_id, manifest in manifests.items():
        assert manifest.id == manifest_id
        assert bool(manifest.name)
        assert len(manifest.stages) > 0

        # Verify each stage exists in registered stages
        for stage_cfg in manifest.stages:
            assert stage_cfg.stage in global_registry.list_names()


def test_manifest_loader_class_and_get_manifest() -> None:
    """Test ManifestLoader caching and get_manifest helper."""
    loader = ManifestLoader()
    manifests = loader.load_all()
    assert 'download_video' in manifests

    found = get_manifest('download_video')
    assert found is not None
    assert found.id == 'download_video'

    missing = get_manifest('non_existent_pipeline')
    assert missing is None
