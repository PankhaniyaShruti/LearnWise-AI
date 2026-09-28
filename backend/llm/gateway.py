"""Central LLM gateway: provider selection, routing, retries, structured output, observability."""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ..config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    GROQ_MODEL_COMPLEX,
    GROQ_MODEL_SIMPLE,
    GROQ_MODEL_STRUCTURED,
    LLM_MAX_RETRIES,
    LLM_PROVIDER,
    LLM_TIMEOUT_SECONDS,
    XAI_API_KEY,
    XAI_BASE_URL,
    XAI_MODEL,
    XAI_MODEL_COMPLEX,
    XAI_MODEL_SIMPLE,
    llm_available,
    missing_llm_message,
)
from ..observability.events import log_usage_event

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMResult:
    def __init__(
        self,
        text: str,
        *,
        model: str,
        provider: str,
        latency_ms: int,
        input_tokens: int | None,
        output_tokens: int | None,
        total_tokens: int | None,
        prompt_name: str,
        prompt_version: str,
        request_id: str,
    ) -> None:
        self.text = text
        self.model = model
        self.provider = provider
        self.latency_ms = latency_ms
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.prompt_name = prompt_name
        self.prompt_version = prompt_version
        self.request_id = request_id


def extract_json(content: str) -> dict | list:
    content = re.sub(r"<think>.*?</think>", "", content or "", flags=re.DOTALL).strip()
    content = re.sub(r"```json\s*", "", content, flags=re.IGNORECASE)
    content = re.sub(r"```\s*", "", content).strip()
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end > start:
        return json.loads(content[start : end + 1])
    start = content.find("[")
    end = content.rfind("]")
    if start != -1 and end > start:
        return json.loads(content[start : end + 1])
    raise ValueError("No JSON object found in model response.")


def select_provider() -> str:
    if LLM_PROVIDER in {"groq", "xai"}:
        if LLM_PROVIDER == "groq" and not GROQ_API_KEY:
            raise RuntimeError("LLM_PROVIDER=groq but GROQ_API_KEY is missing.")
        if LLM_PROVIDER == "xai" and not XAI_API_KEY:
            raise RuntimeError("LLM_PROVIDER=xai but XAI_API_KEY is missing.")
        return LLM_PROVIDER
    if GROQ_API_KEY:
        return "groq"
    if XAI_API_KEY:
        return "xai"
    raise RuntimeError(missing_llm_message())


def select_model(task: str, provider: str) -> str:
    """Route simple / complex / structured / rag tasks to configured models."""
    task = (task or "simple").lower()
    if provider == "groq":
        if task in {"simple", "tutor"}:
            return GROQ_MODEL_SIMPLE or GROQ_MODEL
        if task in {"structured", "quiz", "learn"}:
            return GROQ_MODEL_STRUCTURED or GROQ_MODEL
        if task in {"complex", "planner", "orchestrator", "rag"}:
            return GROQ_MODEL_COMPLEX or GROQ_MODEL
        return GROQ_MODEL
    if task in {"simple", "tutor"}:
        return XAI_MODEL_SIMPLE or XAI_MODEL
    if task in {"complex", "planner", "orchestrator", "rag", "structured", "quiz", "learn"}:
        return XAI_MODEL_COMPLEX or XAI_MODEL
    return XAI_MODEL


def _post_chat(
    *,
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> tuple[str, dict[str, Any]]:
    if provider == "groq":
        url = f"{GROQ_BASE_URL.rstrip('/')}/chat/completions"
        key = GROQ_API_KEY
    else:
        url = f"{XAI_BASE_URL.rstrip('/')}/chat/completions"
        key = XAI_API_KEY
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    with httpx.Client(timeout=LLM_TIMEOUT_SECONDS) as client:
        response = client.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"{provider} API error {response.status_code}: {response.text[:400]}")
        body = response.json()
    text = (((body.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
    usage = body.get("usage") or {}
    return text, usage


def complete(
    messages: list[dict[str, str]],
    *,
    feature: str,
    prompt_name: str,
    prompt_version: str,
    user_email: str | None = None,
    task: str = "simple",
    temperature: float = 0.2,
    max_tokens: int = 2000,
    schema: type[T] | None = None,
    rag_used: bool = False,
    retrieved_chunks: int = 0,
) -> LLMResult | tuple[LLMResult, T]:
    if not llm_available():
        raise RuntimeError(missing_llm_message())

    provider = select_provider()
    model = select_model(task, provider)
    request_id = str(uuid.uuid4())
    last_error: Exception | None = None
    working_messages = list(messages)

    for attempt in range(max(1, LLM_MAX_RETRIES)):
        started = time.perf_counter()
        success = False
        error_type = None
        text = ""
        usage: dict[str, Any] = {}
        try:
            logger.info(
                "LLM call feature=%s prompt=%s@%s provider=%s model=%s attempt=%s",
                feature,
                prompt_name,
                prompt_version,
                provider,
                model,
                attempt + 1,
            )
            text, usage = _post_chat(
                provider=provider,
                model=model,
                messages=working_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            result = LLMResult(
                text=text,
                model=model,
                provider=provider,
                latency_ms=latency_ms,
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                prompt_name=prompt_name,
                prompt_version=prompt_version,
                request_id=request_id,
            )
            if schema is None:
                success = True
                log_usage_event(
                    request_id=request_id,
                    user_email=user_email,
                    feature=feature,
                    model=model,
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    latency_ms=latency_ms,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    total_tokens=result.total_tokens,
                    success=True,
                    rag_used=rag_used,
                    retrieved_chunks=retrieved_chunks,
                )
                return result

            raw = extract_json(text)
            validated = schema.model_validate(raw)
            success = True
            log_usage_event(
                request_id=request_id,
                user_email=user_email,
                feature=feature,
                model=model,
                prompt_name=prompt_name,
                prompt_version=prompt_version,
                latency_ms=latency_ms,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                total_tokens=result.total_tokens,
                success=True,
                rag_used=rag_used,
                retrieved_chunks=retrieved_chunks,
            )
            return result, validated
        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            last_error = error
            error_type = type(error).__name__
            latency_ms = int((time.perf_counter() - started) * 1000)
            logger.warning("Structured output invalid on attempt %s: %s", attempt + 1, error)
            working_messages = list(messages) + [
                {"role": "assistant", "content": text or ""},
                {
                    "role": "user",
                    "content": (
                        "Your previous reply was not valid JSON matching the required schema. "
                        f"Error: {error}. Return ONLY corrected JSON."
                    ),
                },
            ]
        except Exception as error:
            last_error = error
            error_type = type(error).__name__
            latency_ms = int((time.perf_counter() - started) * 1000)
            logger.error("LLM call failed on attempt %s: %s", attempt + 1, error)
        finally:
            if not success:
                log_usage_event(
                    request_id=request_id,
                    user_email=user_email,
                    feature=feature,
                    model=model,
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    latency_ms=latency_ms,
                    input_tokens=usage.get("prompt_tokens"),
                    output_tokens=usage.get("completion_tokens"),
                    total_tokens=usage.get("total_tokens"),
                    success=False,
                    error_type=error_type,
                    rag_used=rag_used,
                    retrieved_chunks=retrieved_chunks,
                )

    raise RuntimeError(f"LLM failed after retries: {last_error}") from last_error
