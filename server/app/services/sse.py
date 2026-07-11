"""Server-Sent Events pour progression longue."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from queue import Empty, Queue
from threading import Thread
from typing import Any

from fastapi.responses import StreamingResponse


def sse_stream(run_task: Callable[[Callable[[dict[str, Any]], None]], None]) -> StreamingResponse:
    queue: Queue[dict[str, Any] | None] = Queue()

    def emit(event: dict[str, Any]) -> None:
        queue.put(event)

    def worker() -> None:
        try:
            run_task(emit)
        except Exception as exc:
            queue.put({"type": "error", "message": str(exc)})
        finally:
            queue.put(None)

    Thread(target=worker, daemon=True).start()

    def generate() -> Iterator[str]:
        while True:
            try:
                item = queue.get(timeout=20)
            except Empty:
                yield ": keepalive\n\n"
                continue
            if item is None:
                break
            yield _sse_line(item)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse_line(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
