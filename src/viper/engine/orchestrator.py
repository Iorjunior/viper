"""Asynchronous DAG pipeline orchestrator with topological execution."""

import asyncio
import inspect
import re
from collections import defaultdict, deque
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
        stages_by_id: dict[str, PipelineStageConfig],
        deps: dict[str, set[str]],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Iterate through topologically sorted ready stage batches."""
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
                output = await self._execute_stage(cfg, context)
                return cfg.id, output

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
    ) -> RunResult:
        """Run the complete pipeline DAG to completion."""
        stages_by_id = {s.id: s for s in manifest.stages}
        deps = {s.id: self._extract_dependencies(s) for s in manifest.stages}

        # Validate DAG structure before starting execution
        self._detect_cycles(manifest.stages, deps)

        context: dict[str, Any] = {
            'inputs': inputs,
            'stages': {},
        }

        try:
            stage_outputs = await self._execute_dag(
                manifest, stages_by_id, deps, context
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
