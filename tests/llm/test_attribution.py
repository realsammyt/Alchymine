"""Tests for the attribution ContextVars that carry a user id to egress.

The three LLM egress sites live under ``alchymine/llm/`` and have no
request, no session and no user. These ContextVars are the only thing that
tells a ledger row who a paid call belongs to, so the properties they rely
on are worth asserting rather than assuming:

- an async generator sees the value its caller set (the SSE path),
- ``asyncio.gather`` branches inherit it (the five-narrative fan-out),
- a value set inside a task cannot leak back out to the next request.
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path

import pytest

from alchymine.llm import attribution
from alchymine.llm.attribution import attributed, current_attribution, set_attribution


class TestLeafModule:
    """It must depend on nothing: both the API and the worker import it."""

    def test_imports_nothing_from_alchymine(self) -> None:
        tree = ast.parse(Path(attribution.__file__).read_text(encoding="utf-8"))
        offenders: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders += [a.name for a in node.names if a.name.startswith("alchymine")]
            elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("alchymine"):
                offenders.append(node.module or "")
        assert offenders == [], f"attribution.py must stay a leaf module; imports {offenders}"


class TestSetAndRead:
    async def test_unset_reads_as_all_none(self) -> None:
        assert current_attribution() == (None, None, None)

    async def test_set_attribution_carries_all_three_fields(self) -> None:
        set_attribution(user_id="u-1", surface="chat", request_id="req-1")
        assert current_attribution() == ("u-1", "chat", "req-1")

    async def test_request_id_defaults_to_none(self) -> None:
        """The Celery path has no HTTP request, and saying so is honest."""
        set_attribution(user_id="u-1", surface="report_narrative")
        assert current_attribution() == ("u-1", "report_narrative", None)


class TestAttributedContextManager:
    async def test_sets_inside_and_restores_outside(self) -> None:
        set_attribution(user_id="outer", surface="chat", request_id="r-outer")
        with attributed(user_id="inner", surface="report_narrative"):
            assert current_attribution() == ("inner", "report_narrative", None)
        assert current_attribution() == ("outer", "chat", "r-outer")

    async def test_restores_even_when_the_body_raises(self) -> None:
        set_attribution(user_id="outer", surface=None)
        with pytest.raises(RuntimeError):
            with attributed(user_id="inner", surface="art"):
                raise RuntimeError("boom")
        assert current_attribution()[0] == "outer"

    async def test_nests(self) -> None:
        with attributed(user_id="a", surface="chat"):
            with attributed(user_id="b", surface="art"):
                assert current_attribution()[:2] == ("b", "art")
            assert current_attribution()[:2] == ("a", "chat")


class TestPropagation:
    async def test_an_async_generator_sees_what_its_caller_set(self) -> None:
        """The SSE shape: StreamingResponse iterates the generator in the
        route handler's task, so the dependency's value is visible inside."""
        seen: list[tuple[str | None, str | None, str | None]] = []

        async def stream():  # noqa: ANN202
            for chunk in ("a", "b"):
                seen.append(current_attribution())
                yield chunk

        async def route() -> None:
            set_attribution(user_id="u-sse", surface="chat", request_id="req-sse")
            generator = stream()
            async for _ in generator:
                pass

        await asyncio.create_task(route())
        assert seen == [("u-sse", "chat", "req-sse"), ("u-sse", "chat", "req-sse")]

    async def test_gather_branches_all_inherit_the_same_user(self) -> None:
        """narrative.py fires five concurrent paid calls through gather."""
        set_attribution(user_id="u-report", surface="report_narrative")

        async def branch(_: int) -> tuple[str | None, str | None, str | None]:
            await asyncio.sleep(0)
            return current_attribution()

        results = await asyncio.gather(*[branch(i) for i in range(5)])
        assert results == [("u-report", "report_narrative", None)] * 5

    async def test_a_value_set_inside_a_task_does_not_leak_out(self) -> None:
        """Each request runs in its own task with its own copied context."""

        async def one_request() -> None:
            set_attribution(user_id="u-leaky", surface="chat")

        await asyncio.create_task(one_request())
        assert current_attribution() == (None, None, None)
