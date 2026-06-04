"""Provider-backed PGG Archon benchmark runner.

Runs benchmark tasks against real or injected model providers, then routes each
model's predictions through the existing PGG Archon integrated benchmark loop.

Boundary: internal model comparison and evolution-queue generation only. This is
not an external AGI benchmark, not full AGI proof, and not legal correctness
proof.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import requests

from agent.agi_task_benchmark import BenchmarkTask
from agent.pgg_archon_benchmark_loop import run_integrated_benchmark

ProviderCall = Callable[["ModelProvider", BenchmarkTask], str]


@dataclass(frozen=True)
class ModelProvider:
    provider_id: str
    model: str
    api_mode: str
    url: str
    api_key_env: str
    max_tokens: int = 512
    temperature: float | None = 0.0


@dataclass(frozen=True)
class ProviderCallOutcome:
    """Auditable raw provider-call outcome before deterministic scoring."""

    prediction: str
    ok: bool
    http_status: int | None = None
    usage: dict[str, Any] | None = None
    attempts: int = 1
    response_preview: str = ""
    error: str | None = None


@dataclass(frozen=True)
class ProviderTaskPrediction:
    provider_id: str
    model: str
    task_id: str
    prediction: str
    ok: bool
    error: str | None = None
    http_status: int | None = None
    usage: dict[str, Any] | None = None
    attempts: int = 1
    response_preview: str = ""


@dataclass(frozen=True)
class ProviderBenchmarkResult:
    schema: str
    generated_at: str
    status: str
    provider: dict[str, Any]
    predictions: list[dict[str, Any]]
    integrated_result: dict[str, Any]
    boundary: str


@dataclass(frozen=True)
class MultiProviderBenchmarkResult:
    schema: str
    generated_at: str
    status: str
    results: list[dict[str, Any]]
    ranking: list[dict[str, Any]]
    boundary: str


def default_pgg_model_providers() -> list[ModelProvider]:
    """Return the configured GPT/Claude/DeepSeek/MiniMax/MiMo/Agnes provider descriptors.

    Reasoning models such as DeepSeek-V4-Flash and MiMo-v2.5-Pro can spend
    small token budgets entirely on ``reasoning_content`` and return
    ``content=\"\"``. Keep their default budgets high enough for visible final
    answers in provider health/evolution gates.
    """
    return [
        ModelProvider("gpt55_5yuantoken", "gpt-5.5", "responses", "https://chuangagent.eu.cc/v1/responses", "GPT55_5YUANTOKEN_API_KEY", max_tokens=1600),
        ModelProvider("claude_opus46_5yuantoken", "claude-opus-4-6", "responses", "https://chuangagent.eu.cc/v1/responses", "CLAUDE_OPUS47_5YUANTOKEN_API_KEY", max_tokens=1600),
        ModelProvider("deepseek_v4_flash", "deepseek-v4-flash", "chat_completions", "https://api.deepseek.com/chat/completions", "DEEPSEEK_V4_FLASH_API_KEY", max_tokens=4096),
        ModelProvider("minimax_m3", "MiniMax-M3", "chat_completions", "https://api.minimax.chat/v1", "MINIMAX_API_KEY", max_tokens=1600),
        ModelProvider("mimo_v25_pro_auditor", "mimo-v2.5-pro", "chat_completions", "https://token-plan-cn.xiaomimimo.com/v1", "MIMO_V25_PRO_API_KEY", max_tokens=4096),
        ModelProvider("agnes_ai", "agnes-2.0-flash", "chat_completions", "https://apihub.agnes-ai.com/v1", "AGNES_AI_API_KEY", max_tokens=1600),
    ]


def load_dotenv_file(path: str | Path = "/Users/appleoppa/.hermes/.env") -> None:
    env_path = Path(path).expanduser()
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _extract_responses_text(data: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, Mapping):
            continue
        for content in item.get("content") or []:
            if isinstance(content, Mapping):
                value = content.get("text") or content.get("content")
                if value:
                    parts.append(str(value))
    return "\n".join(parts).strip() or str(data.get("output_text") or "").strip()


def _provider_prompt(task: BenchmarkTask) -> str:
    return (
        "You are being evaluated by an internal deterministic benchmark. "
        "Answer exactly as requested. Do not add commentary unless the task asks for it.\n\n"
        f"Task ID: {task.task_id}\nDomain: {task.domain}\nPrompt: {task.prompt}"
    )


def call_provider_outcome(provider: ModelProvider, task: BenchmarkTask, *, timeout: int = 180) -> ProviderCallOutcome:
    """Call one provider and preserve audit evidence.

    Some Responses-compatible proxies return HTTP 200 with usage but empty
    ``output``. That is counted as a failed attempt, not as a fabricated answer.
    For Responses mode we retry once with ``max_tokens`` because this local proxy
    has historically accepted that parameter when ``max_completion_tokens``
    produced empty output.
    """
    api_key = os.environ.get(provider.api_key_env)
    if not api_key:
        return ProviderCallOutcome("", False, error=f"missing api key env: {provider.api_key_env}")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    prompt = _provider_prompt(task)
    if provider.api_mode == "responses":
        request_url = provider.url
        attempts: list[dict[str, Any]] = [
            {"model": provider.model, "input": prompt, "max_completion_tokens": provider.max_tokens},
            {"model": provider.model, "input": prompt, "max_tokens": provider.max_tokens},
        ]
    elif provider.api_mode == "chat_completions":
        request_url = provider.url.rstrip("/")
        if not request_url.endswith("/chat/completions"):
            request_url = request_url + "/chat/completions"
        payload: dict[str, Any] = {
            "model": provider.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": provider.max_tokens,
        }
        if provider.temperature is not None:
            payload["temperature"] = provider.temperature
        attempts = [payload]
    else:
        return ProviderCallOutcome("", False, error=f"unsupported api_mode: {provider.api_mode}")

    last_status: int | None = None
    last_usage: dict[str, Any] | None = None
    last_preview = ""
    last_error: str | None = None
    for attempt_index, payload in enumerate(attempts, start=1):
        try:
            response = requests.post(request_url, headers=headers, json=payload, timeout=timeout)
            last_status = response.status_code
            last_preview = response.text[:1000]
            if response.status_code >= 400:
                last_error = f"HTTP {response.status_code}: {response.text[:500]}"
                continue
            data = response.json()
            last_usage = data.get("usage") if isinstance(data, dict) else None
            if provider.api_mode == "responses":
                text = _extract_responses_text(data)
            else:
                text = str(data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            if text:
                return ProviderCallOutcome(text, True, last_status, last_usage, attempt_index, last_preview)
            last_error = "empty prediction text"
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
    return ProviderCallOutcome("", False, last_status, last_usage, len(attempts), last_preview, last_error or "provider call failed")


def call_provider(provider: ModelProvider, task: BenchmarkTask, *, timeout: int = 180) -> str:
    """Call one provider for one task and return raw prediction text."""
    outcome = call_provider_outcome(provider, task, timeout=timeout)
    if not outcome.ok:
        raise RuntimeError(outcome.error or "provider call failed")
    return outcome.prediction


def _call_to_outcome(provider_call: ProviderCall, provider: ModelProvider, task: BenchmarkTask) -> ProviderCallOutcome:
    if provider_call is call_provider:
        return call_provider_outcome(provider, task)
    try:
        text = provider_call(provider, task)
        return ProviderCallOutcome(str(text), True)
    except Exception as exc:  # noqa: BLE001
        return ProviderCallOutcome("", False, error=repr(exc))


def run_provider_benchmark(
    tasks: Sequence[BenchmarkTask],
    provider: ModelProvider,
    *,
    output_dir: str | Path,
    run_id: str | None = None,
    workspace_for_apex: str | Path | None = None,
    provider_call: ProviderCall = call_provider,
) -> ProviderBenchmarkResult:
    """Run tasks through one provider and score using integrated PGG loop."""
    predictions: dict[str, str] = {}
    prediction_records: list[ProviderTaskPrediction] = []
    for task in tasks:
        outcome = _call_to_outcome(provider_call, provider, task)
        predictions[task.task_id] = outcome.prediction if outcome.ok else ""
        prediction_records.append(
            ProviderTaskPrediction(
                provider.provider_id,
                provider.model,
                task.task_id,
                outcome.prediction if outcome.ok else "",
                outcome.ok,
                outcome.error,
                outcome.http_status,
                outcome.usage,
                outcome.attempts,
                outcome.response_preview,
            )
        )

    run_name = run_id or f"{provider.provider_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    provider_out = Path(output_dir).expanduser() / provider.provider_id
    integrated = run_integrated_benchmark(
        tasks,
        predictions,
        output_dir=provider_out,
        run_id=run_name,
        workspace_for_apex=workspace_for_apex,
    )
    status = "PASS" if integrated.status == "PASS" and all(p.ok for p in prediction_records) else "WATCH"
    return ProviderBenchmarkResult(
        schema="PGGArchonProviderBenchmarkResult/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        provider=asdict(provider),
        predictions=[asdict(x) for x in prediction_records],
        integrated_result=integrated.to_json_dict(),
        boundary="Internal provider benchmark comparison only; not external AGI benchmark or full AGI proof.",
    )


def run_multi_provider_benchmark(
    tasks: Sequence[BenchmarkTask],
    providers: Sequence[ModelProvider],
    *,
    output_dir: str | Path,
    workspace_for_apex: str | Path | None = None,
    provider_call: ProviderCall = call_provider,
) -> MultiProviderBenchmarkResult:
    """Run benchmark tasks across providers and rank by integrated score."""
    results = [
        run_provider_benchmark(
            tasks,
            provider,
            output_dir=output_dir,
            run_id=f"{provider.provider_id}-benchmark",
            workspace_for_apex=workspace_for_apex,
            provider_call=provider_call,
        )
        for provider in providers
    ]
    ranking = []
    for result in results:
        run = result.integrated_result["benchmark_run"]
        ranking.append({
            "provider_id": result.provider["provider_id"],
            "model": result.provider["model"],
            "status": result.status,
            "weighted_score": run["weighted_score"],
            "passed_tasks": run["passed_tasks"],
            "total_tasks": run["total_tasks"],
            "evolution_queue_count": result.integrated_result["evolution_queue_count"],
        })
    ranking.sort(key=lambda x: (x["weighted_score"], x["passed_tasks"]), reverse=True)
    overall_status = "PASS" if all(item.status == "PASS" for item in results) else "WATCH"
    return MultiProviderBenchmarkResult(
        schema="PGGArchonMultiProviderBenchmarkResult/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=overall_status,
        results=[asdict(x) for x in results],
        ranking=ranking,
        boundary="Internal multi-provider comparison; not external AGI benchmark or full AGI proof.",
    )


def write_multi_provider_result(result: MultiProviderBenchmarkResult, output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "multi_provider_benchmark.json"
    path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    ranking_path = out / "multi_provider_ranking.json"
    ranking_path.write_text(json.dumps(result.ranking, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"result": str(path), "ranking": str(ranking_path)}
