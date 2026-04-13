"""Client-side pagination for API responses that return large lists."""

from __future__ import annotations

import json
from typing import Any

# Sensible default — keeps responses well under typical LLM context limits.
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def paginate_response(
    data: Any,
    *,
    pagina: int = 1,
    itens_por_pagina: int = DEFAULT_PAGE_SIZE,
    list_key: str = "dados",
) -> str:
    """Apply client-side pagination to an API response.

    Expects *data* to be either:
      - a dict with a list under *list_key*  (e.g. {"dados": [...]})
      - a plain list

    Returns a JSON string with:
      - The sliced items under *list_key* (or as top-level list)
      - A "_paginacao" metadata object with total, page info, and hints
    """
    # Extract the items list
    if isinstance(data, dict) and list_key in data:
        items = data[list_key]
        extra_keys = {k: v for k, v in data.items() if k != list_key}
    elif isinstance(data, list):
        items = data
        extra_keys = {}
    else:
        # Not a pageable response (e.g. scalar/summary) — return as-is
        return json.dumps(data, ensure_ascii=False, default=str)

    if not isinstance(items, list):
        return json.dumps(data, ensure_ascii=False, default=str)

    total = len(items)
    page_size = max(1, min(itens_por_pagina, MAX_PAGE_SIZE))
    page = max(1, pagina)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)

    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]

    result: dict[str, Any] = {**extra_keys}
    result[list_key] = page_items
    result["_paginacao"] = {
        "pagina": page,
        "itens_por_pagina": page_size,
        "total_itens": total,
        "total_paginas": total_pages,
    }

    return json.dumps(result, ensure_ascii=False, default=str)
