from __future__ import annotations

from typing import Any, Protocol


class AsyncContentGenerator(Protocol):
    async def generate_content(
        self,
        *,
        model: str,
        contents: str,
        config: Any,
    ) -> Any: ...
