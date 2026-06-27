# --- FUSION: create_resilient_client ---
# parent_a: agent_runtime_helpers.create_openai_client
# parent_b: agent_runtime_helpers.recover_with_credential_pool
# fusion_strategy: 客户端创建 × 凭证恢复交叉遗传
# generated_by: gpt55_gene_fusion

from __future__ import annotations

import inspect
from typing import Any, Mapping, Optional, Tuple


def create_resilient_client(
    agent: Any,
    client_kwargs: Mapping[str, Any] | None,
    *,
    credential_pool: Any,
) -> Tuple[Any, Optional[BaseException]]:
    """Create an OpenAI-compatible client with credential-pool failover.

    Inherited from create_openai_client:
      - Provider-specific OpenAI-compatible client construction
        (Copilot ACP / Gemini Cloud Code / Gemini Native adaptations)
      - TCP keepalive injection for dead-peer detection
      - WAF header cleanup for Chuangagent providers
      - base_url / proxy env validation

    Inherited from recover_with_credential_pool:
      - Reason-aware recovery: billing→rotate, rate_limit→retry/rotate, auth→refresh/rotate
      - Provider contamination guard (prevents pool from mutating wrong provider's state)
      - xAI OAuth entitlement detection (prevents refresh loop on unsubscribed accounts)

    Returns:
        (client, None) on success.
        (None, last_error) if all credentials/recovery attempts are exhausted.
    """
    kwargs: dict[str, Any] = dict(client_kwargs or {})
    max_attempts = _fusion_pool_size(credential_pool) or 1
    attempted_fingerprints: set[str] = set()
    last_error: Optional[BaseException] = None

    def _make_client() -> Any:
        factory = globals().get("create_openai_client")
        if not callable(factory):
            raise RuntimeError("create_openai_client not available")
        try:
            return factory(agent, kwargs)
        except TypeError:
            return factory(agent, **kwargs)

    # Fast path: creation succeeds with current credential
    try:
        return _make_client(), None
    except BaseException as exc:
        last_error = exc

    # Recovery path: each credential entry max one attempt
    for _ in range(max_attempts):
        reason = _fusion_classify_failover_reason(last_error)
        before_fp = _fusion_credential_fingerprint(agent, kwargs, credential_pool)

        if before_fp in attempted_fingerprints:
            break
        attempted_fingerprints.add(before_fp)

        # Call recover_with_credential_pool with the detected reason
        recovered = _fusion_call_recover_with_credential_pool(
            agent=agent,
            credential_pool=credential_pool,
            reason=reason,
            error=last_error,
        )

        if _fusion_recovery_succeeded(recovered):
            _fusion_apply_recovered_credentials(kwargs, recovered)
            try:
                return _make_client(), None
            except BaseException as exc:
                last_error = exc
                continue
        break

    return None, last_error


def _fusion_pool_size(pool: Any) -> int:
    """Get the number of credential entries in a pool."""
    if pool is None:
        return 0
    if hasattr(pool, "__len__"):
        return len(pool)
    if hasattr(pool, "entries"):
        return len(pool.entries)
    if hasattr(pool, "credentials"):
        return len(pool.credentials)
    return 0


def _fusion_credential_fingerprint(agent: Any, kwargs: dict, pool: Any) -> str:
    """Unique fingerprint of current credential configuration."""
    parts = []
    if pool and hasattr(pool, "current"):
        try:
            cur = pool.current()
            if cur and hasattr(cur, "id"):
                parts.append(str(cur.id))
            elif cur and hasattr(cur, "api_key"):
                parts.append(str(hash(cur.api_key)))
        except Exception:
            pass
    api_key = kwargs.get("api_key", "") or getattr(agent, "api_key", "")
    if api_key:
        parts.append(str(hash(api_key)))
    base_url = kwargs.get("base_url", "") or getattr(agent, "base_url", "")
    if base_url:
        parts.append(str(hash(base_url)))
    provider = getattr(agent, "provider", "")
    if provider:
        parts.append(provider)
    return ":".join(parts)


def _fusion_classify_failover_reason(error: BaseException | None) -> str:
    """Map provider exceptions to failover reason."""
    text = ""
    status = None
    if error is not None:
        text = f"{type(error).__name__}: {error}".lower()
        status = (
            getattr(error, "status_code", None)
            or getattr(error, "status", None)
            or getattr(getattr(error, "response", None), "status_code", None)
            or getattr(getattr(error, "response", None), "status", None)
        )
    if status in (401, 403):
        return "auth"
    if status == 429:
        return "rate_limit"
    if status in (402, 4020):
        return "billing"
    if any(s in text for s in ("billing", "payment", "insufficient_balance",
                               "spend limit", "out of credits")):
        return "billing"
    if any(s in text for s in ("rate limit", "rate_limit", "too many requests", "quota")):
        return "rate_limit"
    if any(s in text for s in ("unauthorized", "forbidden", "invalid api key",
                               "expired token", "oauth", "entitlement")):
        return "auth"
    return "rate_limit"


def _fusion_call_recover_with_credential_pool(
    *,
    agent: Any,
    credential_pool: Any,
    reason: str,
    error: BaseException | None,
) -> Any:
    """Call recover_with_credential_pool across possible signatures."""
    recover = globals().get("recover_with_credential_pool")
    if not callable(recover):
        return RuntimeError("recover_with_credential_pool not available")

    try:
        sig = inspect.signature(recover)
        params = list(sig.parameters.keys())
        kwargs = {}
        # Map by parameter name
        arg_map = {
            "agent": agent,
            "status_code": getattr(error, "status_code", None),
            "has_retried_429": False,
            "classified_reason": reason,
            "error_context": {"reason": reason, "error": str(error) if error else ""},
        }
        for p in params:
            if p in arg_map:
                kwargs[p] = arg_map[p]
        return recover(**kwargs)
    except Exception:
        return False


def _fusion_recovery_succeeded(result: Any) -> bool:
    """Normalize recovery outcomes."""
    if result is None or result is False:
        return False
    if isinstance(result, BaseException):
        return False
    if isinstance(result, tuple):
        return bool(result[0]) if result else False
    if isinstance(result, dict):
        if "ok" in result:
            return bool(result["ok"])
        if "success" in result:
            return bool(result["success"])
        if "credential" in result or "access_token" in result:
            return True
    return True


def _fusion_apply_recovered_credentials(kwargs: dict, recovered: Any) -> None:
    """Merge recovered credentials into client kwargs."""
    if isinstance(recovered, dict):
        for key in ("api_key", "base_url", "access_token"):
            if key in recovered:
                kwargs[key] = recovered[key]
    elif isinstance(recovered, tuple) and len(recovered) >= 2:
        if recovered[1] and isinstance(recovered[1], dict):
            for key in ("api_key", "base_url", "access_token"):
                if key in recovered[1]:
                    kwargs[key] = recovered[1][key]

# --- END FUSION ---
