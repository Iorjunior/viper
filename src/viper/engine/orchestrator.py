"""Asynchronous DAG pipeline orchestrator with topological execution."""

import asyncio
import inspect
import re
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from viper.engine.interpolator import resolve_inputs
from viper.engine.models import (
    PipelineManifest,
    PipelineStageConfig,
    RunResult,
    RunStatus,
)
from viper.engine.registry import StageRegistry, global_registry

STAGE_DEP_PATTERN = re.compile(r'stages\.([a-zA-Z0-9_-]+)')

StageStartHook = Callable[[str], Awaitable[None]]
StageCompleteHook = Callable[[str, Any], Awaitable[None]]
StageErrorHook = Callable[[str, Exception], Awaitable[None]]


@dataclass
class StageHooks:
    """Optional callbacks for stage lifecycle observation."""

    on_start: StageStartHook | None = None
    on_complete: StageCompleteHook | None = None
    on_error: StageErrorHook | None = None


class Orchestrator:
    """Executes a pipeline DAG with dependency resolution and concurrency."""

    def __init__(self, registry: StageRegistry | None = None) -> None:
        self.registry = registry or global_registry

    @staticmethod
    def _extract_dependencies(stage_cfg: PipelineStageConfig) -> set[str]:
        """Extract referenced stage IDs from input template expressions."""
        deps: set[str] = set()

        def _scan(val: Any) -> None:
            if isinstance(val, str):
                for match in STAGE_DEP_PATTERN.finditer(val):
                    deps.add(match.group(1))
            elif isinstance(val, dict):
                for sub in val.values():
                    _scan(sub)
            elif isinstance(val, list):
                for item in val:
                    _scan(item)

        _scan(stage_cfg.inputs)
        return deps

    @staticmethod
    def _detect_cycles(
        stages: list[PipelineStageConfig],
        deps: dict[str, set[str]],
    ) -> None:
        """Verify the graph is a valid DAG using Kahn's algorithm."""
        in_degree: dict[str, int] = {s.id: len(deps[s.id]) for s in stages}
        queue: deque[str] = deque([
            s_id for s_id, degree in in_degree.items() if degree == 0
        ])
        visited = 0

        # Build reverse adjacency map (dependency -> dependents)
        dependents: dict[str, list[str]] = defaultdict(list)
        for s_id, s_deps in deps.items():
            for dep in s_deps:
                dependents[dep].append(s_id)

        while queue:
            node = queue.popleft()
            visited += 1
            for dependent in dependents[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if visited != len(stages):
            msg = 'Cycle detected in pipeline DAG specification'
            raise ValueError(msg)

    async def _execute_stage(
        self,
        stage_cfg: PipelineStageConfig,
        context: dict[str, Any],
    ) -> Any:
        """Resolve inputs and execute a single stage function."""
        stage_def = self.registry.get(stage_cfg.stage)
        if stage_def is None or stage_def.fn is None:
            msg = f"Stage '{stage_cfg.stage}' is not registered"
            raise RuntimeError(msg)

        resolved_inputs = resolve_inputs(stage_cfg.inputs, context)

        fn = stage_def.fn
        if inspect.iscoroutinefunction(fn):
            return await fn(**resolved_inputs)
        return await asyncio.to_thread(fn, **resolved_inputs)

    async def _execute_dag(
        self,
        manifest: PipelineManifest,
        deps: dict[str, set[str]],
        context: dict[str, Any],
        hooks: StageHooks,
    ) -> dict[str, Any]:
        """Iterate through topologically sorted ready stage batches."""
        stages_by_id = {s.id: s for s in manifest.stages}
        completed_stages: set[str] = set()

        while len(completed_stages) < len(manifest.stages):
            ready_stages = [
                stages_by_id[s_id]
                for s_id, s_deps in deps.items()
                if s_id not in completed_stages
                and s_deps.issubset(completed_stages)
            ]

            if not ready_stages:
                msg = 'Pipeline deadlocked: unable to resolve dependencies'
                raise RuntimeError(msg)

            async def _run_and_record(
                cfg: PipelineStageConfig,
            ) -> tuple[str, Any]:
                if hooks.on_start:
                    await hooks.on_start(cfg.id)
                try:
                    output = await self._execute_stage(cfg, context)
                    if hooks.on_complete:
                        await hooks.on_complete(cfg.id, output)
                    return cfg.id, output
                except Exception as exc:
                    if hooks.on_error:
                        await hooks.on_error(cfg.id, exc)
                    raise

            tasks = [_run_and_record(cfg) for cfg in ready_stages]
            results = await asyncio.gather(*tasks)

            for stage_id, output in results:
                context['stages'][stage_id] = {'output': output}
                completed_stages.add(stage_id)

        return {
            s_id: data.get('output')
            for s_id, data in context['stages'].items()
        }

    async def run(
        self,
        manifest: PipelineManifest,
        inputs: dict[str, Any],
        *,
        on_stage_start: StageStartHook | None = None,
        on_stage_complete: StageCompleteHook | None = None,
        on_stage_error: StageErrorHook | None = None,
    ) -> RunResult:
        """Run the complete pipeline DAG to completion."""
        deps = {s.id: self._extract_dependencies(s) for s in manifest.stages}

        # Validate DAG structure before starting execution
        self._detect_cycles(manifest.stages, deps)

        context: dict[str, Any] = {
            'inputs': inputs,
            'stages': {},
        }
        hooks = StageHooks(
            on_start=on_stage_start,
            on_complete=on_stage_complete,
            on_error=on_stage_error,
        )

        try:
            stage_outputs = await self._execute_dag(
                manifest,
                deps,
                context,
                hooks,
            )
            return RunResult(
                status=RunStatus.COMPLETED,
                stage_results=stage_outputs,
            )
        except Exception as err:
            return RunResult(
                status=RunStatus.FAILED,
                error=str(err),
            )
