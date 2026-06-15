from __future__ import annotations

import os
import inspect
from contextlib import contextmanager, nullcontext
from typing import Any

from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("LANGFUSE_HOST") and not os.getenv("LANGFUSE_BASE_URL"):
    os.environ["LANGFUSE_BASE_URL"] = os.environ["LANGFUSE_HOST"]
if os.getenv("LANGFUSE_BASE_URL") and not os.getenv("LANGFUSE_HOST"):
    os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]

try:
    from langfuse import get_client, observe as _langfuse_observe
except Exception:  # pragma: no cover
    try:
        from langfuse.decorators import observe as _langfuse_observe, langfuse_context
    except Exception:  # pragma: no cover
        def _langfuse_observe(*args: Any, **kwargs: Any):
            def decorator(func):
                return func
            return decorator

        class _DummyContext:
            def update_current_trace(self, **kwargs: Any) -> None:
                return None

            def update_current_observation(self, **kwargs: Any) -> None:
                return None

            def flush(self) -> None:
                return None

        langfuse_context = _DummyContext()

    def observe(*args: Any, **kwargs: Any):
        try:
            return _langfuse_observe(*args, **kwargs)
        except TypeError:
            kwargs.pop("capture_input", None)
            kwargs.pop("capture_output", None)
            return _langfuse_observe(*args, **kwargs)

    @contextmanager
    def trace_attributes(**_: Any):
        yield

    @contextmanager
    def generation_observation(*_: Any, **__: Any):
        yield None

    def update_current_observation(**kwargs: Any) -> None:
        langfuse_context.update_current_observation(**kwargs)

    def update_current_trace(**_: Any) -> None:
        return None

    def update_observation(observation: Any, **kwargs: Any) -> None:
        if observation is not None and hasattr(observation, "update"):
            observation.update(**kwargs)

    def flush_traces() -> None:
        flush = getattr(langfuse_context, "flush", None)
        if callable(flush):
            flush()
else:
    try:
        from langfuse import propagate_attributes as _propagate_attributes
    except Exception:  # pragma: no cover
        _propagate_attributes = None

    def observe(*args: Any, **kwargs: Any):
        try:
            return _langfuse_observe(*args, **kwargs)
        except TypeError:
            kwargs.pop("capture_input", None)
            kwargs.pop("capture_output", None)
            return _langfuse_observe(*args, **kwargs)

    def _client() -> Any:
        return get_client()

    @contextmanager
    def trace_attributes(
        *,
        user_id: str,
        session_id: str,
        feature: str,
        model: str,
        correlation_id: str | None = None,
    ):
        metadata = {"feature": feature, "model": model}
        if correlation_id:
            metadata["correlation_id"] = correlation_id

        if _propagate_attributes is None:
            yield
        else:
            with _propagate_attributes(
                trace_name="chat-response",
                user_id=user_id,
                session_id=session_id,
                tags=["lab", feature, model],
                metadata=metadata,
            ):
                yield

    def update_current_trace(**kwargs: Any) -> None:
        client = _client()
        if hasattr(client, "update_current_trace"):
            client.update_current_trace(**kwargs)

    @contextmanager
    def generation_observation(
        *,
        name: str,
        model: str,
        input_data: dict[str, Any],
    ):
        client = _client()
        if hasattr(client, "start_as_current_observation"):
            with client.start_as_current_observation(
                as_type="generation",
                name=name,
                model=model,
                input=input_data,
            ) as observation:
                yield observation
        elif hasattr(client, "start_as_current_generation"):
            with client.start_as_current_generation(
                name=name,
                model=model,
                input=input_data,
            ) as observation:
                yield observation
        else:
            with nullcontext(None) as observation:
                yield observation

    def update_current_observation(**kwargs: Any) -> None:
        client = _client()
        usage_details = kwargs.pop("usage_details", None)
        if usage_details:
            metadata = kwargs.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            metadata["usage_details"] = usage_details
            kwargs["metadata"] = metadata

        if hasattr(client, "update_current_span"):
            params = inspect.signature(client.update_current_span).parameters
            client.update_current_span(**{key: value for key, value in kwargs.items() if key in params})
        elif hasattr(client, "update_current_observation"):
            params = inspect.signature(client.update_current_observation).parameters
            client.update_current_observation(**{key: value for key, value in kwargs.items() if key in params})

    def update_observation(observation: Any, **kwargs: Any) -> None:
        if observation is not None and hasattr(observation, "update"):
            params = inspect.signature(observation.update).parameters
            observation.update(**{key: value for key, value in kwargs.items() if key in params})

    def flush_traces() -> None:
        client = _client()
        if hasattr(client, "flush"):
            client.flush()


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
