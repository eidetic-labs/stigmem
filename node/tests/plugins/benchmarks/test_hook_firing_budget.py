from __future__ import annotations

import os
import statistics
import time

import pytest

from stigmem_node.plugins import Allow, HookRegistry, PluginContext, PluginManifest

pytestmark = pytest.mark.skipif(
    os.getenv("STIGMEM_RUN_PLUGIN_BENCHMARKS") != "1",
    reason="plugin hook microbenchmarks run only in the dedicated benchmark gate",
)

_BUDGET_NS = 10_000
_ITERATIONS = 5_000


def _manifest(name: str, hook: str, handler: object) -> PluginManifest:
    return PluginManifest(name=name, version="1.0.0", hooks={hook: handler})


def _p99_ns(samples: list[int]) -> float:
    return statistics.quantiles(samples, n=100, method="inclusive")[98]


def _measure(callable_under_test: object) -> float:
    fn = callable_under_test  # local binding keeps loop overhead stable
    samples: list[int] = []
    for _ in range(_ITERATIONS):
        start = time.perf_counter_ns()
        fn()  # type: ignore[operator]
        samples.append(time.perf_counter_ns() - start)
    return _p99_ns(samples)


@pytest.mark.parametrize("handler_count", [0, 1, 3])
def test_voting_hook_firing_p99_under_10us(handler_count: int) -> None:
    registry = HookRegistry()

    def handler(_ctx: PluginContext, **_: object) -> Allow:
        return Allow()

    for idx in range(handler_count):
        registry.register_plugin(_manifest(f"plug-{idx}", "pre_assert_authorize", handler))

    p99_ns = _measure(lambda: registry.fire_voting("pre_assert_authorize"))

    assert p99_ns < _BUDGET_NS, f"voting p99 {p99_ns / 1000:.2f} us exceeds 10 us"


@pytest.mark.parametrize("handler_count", [0, 1, 3])
def test_filter_chain_hook_firing_p99_under_10us(handler_count: int) -> None:
    registry = HookRegistry()

    def handler(_ctx: PluginContext, value: str, **_: object) -> str:
        return value

    for idx in range(handler_count):
        registry.register_plugin(_manifest(f"plug-{idx}", "recall_filter", handler))

    p99_ns = _measure(lambda: registry.fire_filter_chain("recall_filter", "value"))

    assert p99_ns < _BUDGET_NS, f"filter-chain p99 {p99_ns / 1000:.2f} us exceeds 10 us"


@pytest.mark.parametrize("handler_count", [0, 1, 3])
def test_score_delta_hook_firing_p99_under_10us(handler_count: int) -> None:
    registry = HookRegistry()

    def handler(
        _ctx: PluginContext, _scored_results: list[object], **_: object
    ) -> dict[str, float]:
        return {}

    for idx in range(handler_count):
        registry.register_plugin(_manifest(f"plug-{idx}", "recall_rank", handler))

    p99_ns = _measure(lambda: registry.fire_score_delta("recall_rank", []))

    assert p99_ns < _BUDGET_NS, f"score-delta p99 {p99_ns / 1000:.2f} us exceeds 10 us"


@pytest.mark.parametrize("handler_count", [0, 1, 3])
def test_fire_and_forget_hook_firing_p99_under_10us(handler_count: int) -> None:
    registry = HookRegistry()

    def handler(_ctx: PluginContext, **_: object) -> None:
        return None

    for idx in range(handler_count):
        registry.register_plugin(_manifest(f"plug-{idx}", "post_assert_persist", handler))

    p99_ns = _measure(lambda: registry.fire_fire_and_forget("post_assert_persist"))

    assert p99_ns < _BUDGET_NS, f"fire-and-forget p99 {p99_ns / 1000:.2f} us exceeds 10 us"
