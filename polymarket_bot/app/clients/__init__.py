"""HTTP and SDK clients — lazy exports so `import app.clients` does not load py_clob_client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["ClobWrapper", "DataApiClient", "GammaClient"]

if TYPE_CHECKING:
    from app.clients.clob_client import ClobWrapper
    from app.clients.data_client import DataApiClient
    from app.clients.gamma_client import GammaClient


def __getattr__(name: str) -> Any:
    if name == "ClobWrapper":
        from app.clients.clob_client import ClobWrapper

        return ClobWrapper
    if name == "DataApiClient":
        from app.clients.data_client import DataApiClient

        return DataApiClient
    if name == "GammaClient":
        from app.clients.gamma_client import GammaClient

        return GammaClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
