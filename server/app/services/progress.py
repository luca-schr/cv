"""Callbacks de progression (génération, export PDF)."""

from __future__ import annotations

from collections.abc import Callable

ProgressFn = Callable[[str, str, int | None], None]

NO_PROGRESS: ProgressFn = lambda _step, _label, _pct=None: None
