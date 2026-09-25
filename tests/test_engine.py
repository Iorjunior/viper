"""Unit tests for Viper Core Engine: assets, stage decorator, DAG runner."""

import asyncio
from pathlib import Path
from typing import Any

import pytest

from viper.engine.assets import (
    AudioAsset,
    BaseAsset,
    TextAsset,
    VideoAsset,
)
from viper.engine.decorator import stage
from viper.engine.interpolator import resolve_inputs, resolve_template
from viper.engine.models import (
    PipelineInput,
    PipelineManifest,
    PipelineStageConfig,
    RunStatus,
)
from viper.engine.orchestrator import Orchestrator
from viper.engine.registry import StageRegistry


def test_asset_models(tmp_path: Path) -> None:
    audio_file = tmp_path / 'sample.wav'
    audio_file.write_bytes(b'wav')

    audio = AudioAsset(path=audio_file, duration=12.5, sample_rate=24000)
    assert str(audio) == str(audio_file)
    assert audio.duration == 12.5
    assert audio.sample_rate == 24000
    assert isinstance(audio, BaseAsset)

    video_file = tmp_path / 'sample.mp4'
    video_file.write_bytes(b'mp4')
    video = VideoAsset(path=video_file, duration=60.0, resolution='1920x1080')
    assert str(video) == str(video_file)
    assert video.resolution == '1920x1080'

    text = TextAsset(content='Hello viper')
    assert text.content == 'Hello viper'


def test_stage_decorator_and_registry() -> None:
    registry = StageRegistry()

    @stage(name='test_echo', description='Echoes input', registry=registry)
    def echo_stage(message: str) -> dict[str, str]:
        return {'echoed': message}

    definition = registry.get('test_echo')
    assert definition is not None
    assert definition.name == 'test_echo'
    assert definition.description == 'Echoes input'
    assert 'message' in definition.inputs

    # Calling decorated function directly works as normal
    result = echo_stage(message='viper')
    assert result == {'echoed': 'viper'}


def test_interpolator() -> None:
    context: dict[str, Any] = {
        'inputs': {
            'video_url': 'https://youtube.com/watch?v=123',
            'count': 3,
        },
        'stages': {
            'step_download': {
                'output': {
                    'video_path': '/tmp/video.mp4',
                }
            }
        },
    }

    assert (
        resolve_template('{{ inputs.video_url }}', context)
        == 'https://youtube.com/watch?v=123'
    )
    tmpl = '{{ stages.step_download.output.video_path }}'
    assert resolve_template(tmpl, context) == '/tmp/video.mp4'

    unresolved = resolve_template('literal value', context)
    assert unresolved == 'literal value'

    raw_inputs = {
        'url': '{{ inputs.video_url }}',
        'file': '{{ stages.step_download.output.video_path }}',
        'times': '{{ inputs.count }}',
        'constant': 42,
    }
    resolved = resolve_inputs(raw_inputs, context)
    assert resolved == {
        'url': 'https://youtube.com/watch?v=123',
        'file': '/tmp/video.mp4',
        'times': 3,
        'constant': 42,
    }


@pytest.mark.asyncio
async def test_orchestrator_linear_pipeline() -> None:
    registry = StageRegistry()

    @stage(name='add_one', registry=registry)
    def add_one_stage(val: int) -> dict[str, int]:
        return {'result': val + 1}

    @stage(name='multiply_two', registry=registry)
    async def multiply_two_stage(val: int) -> dict[str, int]:
        await asyncio.sleep(0.01)
        return {'result': val * 2}

    manifest = PipelineManifest(
        id='linear_test',
        name='Linear Test',
        inputs=[PipelineInput(name='start_val', type='int')],
        stages=[
            PipelineStageConfig(
                id='step1',
                stage='add_one',
                inputs={'val': '{{ inputs.start_val }}'},
            ),
            PipelineStageConfig(
                id='step2',
                stage='multiply_two',
                inputs={'val': '{{ stages.step1.output.result }}'},
            ),
        ],
    )

    orchestrator = Orchestrator(registry=registry)
    run_result = await orchestrator.run(manifest, inputs={'start_val': 5})

    assert run_result.status == RunStatus.COMPLETED
    assert run_result.stage_results['step1']['result'] == 6
    assert run_result.stage_results['step2']['result'] == 12


@pytest.mark.asyncio
async def test_orchestrator_parallel_branches() -> None:
    registry = StageRegistry()
    execution_order: list[str] = []

    @stage(name='source', registry=registry)
    def source_stage() -> dict[str, int]:
        execution_order.append('source')
        return {'val': 10}

    @stage(name='branch_a', registry=registry)
    async def branch_a_stage(val: int) -> dict[str, int]:
        await asyncio.sleep(0.02)
        execution_order.append('branch_a')
        return {'res_a': val + 5}

    @stage(name='branch_b', registry=registry)
    async def branch_b_stage(val: int) -> dict[str, int]:
        await asyncio.sleep(0.01)
        execution_order.append('branch_b')
        return {'res_b': val * 2}

    @stage(name='join', registry=registry)
    def join_stage(a: int, b: int) -> dict[str, int]:
        execution_order.append('join')
        return {'total': a + b}

    manifest = PipelineManifest(
        id='parallel_test',
        name='Parallel Test',
        stages=[
            PipelineStageConfig(id='src', stage='source'),
            PipelineStageConfig(
                id='ba',
                stage='branch_a',
                inputs={'val': '{{ stages.src.output.val }}'},
            ),
            PipelineStageConfig(
                id='bb',
                stage='branch_b',
                inputs={'val': '{{ stages.src.output.val }}'},
            ),
            PipelineStageConfig(
                id='final',
                stage='join',
                inputs={
                    'a': '{{ stages.ba.output.res_a }}',
                    'b': '{{ stages.bb.output.res_b }}',
                },
            ),
        ],
    )

    orchestrator = Orchestrator(registry=registry)
    run_result = await orchestrator.run(manifest, inputs={})

    assert run_result.status == RunStatus.COMPLETED
    assert run_result.stage_results['final']['total'] == 35  # (10+5) + (10*2)
    assert execution_order[0] == 'source'
    assert execution_order[-1] == 'join'
    # branch_a and branch_b ran concurrently in the middle
    assert set(execution_order[1:3]) == {'branch_a', 'branch_b'}


@pytest.mark.asyncio
async def test_orchestrator_cycle_detection() -> None:
    registry = StageRegistry()

    @stage(name='dummy', registry=registry)
    def dummy_stage(x: int) -> dict[str, int]:
        return {'x': x}

    manifest = PipelineManifest(
        id='cycle_test',
        name='Cycle Test',
        stages=[
            PipelineStageConfig(
                id='step1',
                stage='dummy',
                inputs={'x': '{{ stages.step2.output.x }}'},
            ),
            PipelineStageConfig(
                id='step2',
                stage='dummy',
                inputs={'x': '{{ stages.step1.output.x }}'},
            ),
        ],
    )

    orchestrator = Orchestrator(registry=registry)
    with pytest.raises(ValueError, match='Cycle detected'):
        await orchestrator.run(manifest, inputs={})


@pytest.mark.asyncio
async def test_orchestrator_stage_failure() -> None:
    registry = StageRegistry()

    @stage(name='failing_stage', registry=registry)
    def fail_stage() -> None:
        msg = 'Fatal processing error'
        raise RuntimeError(msg)

    manifest = PipelineManifest(
        id='fail_test',
        name='Fail Test',
        stages=[PipelineStageConfig(id='s1', stage='failing_stage')],
    )

    orchestrator = Orchestrator(registry=registry)
    run_result = await orchestrator.run(manifest, inputs={})

    assert run_result.status == RunStatus.FAILED
    assert 'Fatal processing error' in str(run_result.error)


@pytest.mark.asyncio
async def test_orchestrator_observability_hooks() -> None:
    registry = StageRegistry()
    events: list[tuple[str, str, Any]] = []

    @stage(name='step_ok', registry=registry)
    def ok_fn(val: int) -> int:
        return val * 2

    @stage(name='step_err', registry=registry)
    def err_fn() -> None:
        raise ValueError('boom')

    manifest = PipelineManifest(
        id='hook_test',
        name='Hook Test',
        stages=[
            PipelineStageConfig(
                id='first',
                stage='step_ok',
                inputs={'val': 5},
            ),
            PipelineStageConfig(
                id='second',
                stage='step_err',
                inputs={},
            ),
        ],
    )

    async def on_start(stage_id: str) -> None:
        events.append(('start', stage_id, None))

    async def on_complete(stage_id: str, output: Any) -> None:
        events.append(('complete', stage_id, output))

    async def on_error(stage_id: str, exc: Exception) -> None:
        events.append(('error', stage_id, str(exc)))

    orchestrator = Orchestrator(registry=registry)
    res = await orchestrator.run(
        manifest,
        inputs={},
        on_stage_start=on_start,
        on_stage_complete=on_complete,
        on_stage_error=on_error,
    )

    assert res.status == RunStatus.FAILED
    assert ('start', 'first', None) in events
    assert ('complete', 'first', 10) in events
    assert ('start', 'second', None) in events
    assert ('error', 'second', 'boom') in events
