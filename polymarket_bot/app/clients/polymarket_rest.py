"""Unified REST facade over Gamma + CLOB + Data (keeps HTTP clients in one place)."""

from __future__ import annotations

from app.clients.clob_client import ClobWrapper
from app.clients.data_client import DataApiClient
from app.clients.gamma_client import GammaClient
from app.config import Settings


class PolymarketRestFacade:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.gamma = GammaClient(settings)
        self.clob = ClobWrapper(settings)
        self.data = DataApiClient(settings)

    def close(self) -> None:
        self.gamma.close()
        self.data.close()
