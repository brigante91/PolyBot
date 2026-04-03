"""Live microstructure metrics per market (REST polling; WS can extend)."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING

from app.clients.clob_client import ClobWrapper
from app.config import Settings
from app.models.candidate import CandidateMarket
from app.models.context import LiveFeatures
from app.models.orderbook import OrderBookSnapshot
from app.analysis.feature_builder import normalize_imbalance

if TYPE_CHECKING:
    from app.execution.ws_handler import WsMarketHub


class LiveMarketAnalyzer:
    def __init__(
        self,
        settings: Settings,
        clob: ClobWrapper,
        *,
        ws_hub: WsMarketHub | None = None,
    ) -> None:
        self._settings = settings
        self._clob = clob
        self._ws_hub = ws_hub
        self._mid_history: dict[str, list[tuple[float, float]]] = defaultdict(list)

    def analyze(self, candidate: CandidateMarket, token_id: str | None = None) -> LiveFeatures:
        tid = token_id or candidate.primary_token_id()
        if not tid:
            return LiveFeatures()
        book: OrderBookSnapshot | None = None
        if self._ws_hub is not None:
            wb = self._ws_hub.get_book(tid)
            if wb is not None and (wb.best_bid is not None or wb.best_ask is not None):
                book = wb
        if book is None:
            book = self._clob.get_order_book(tid)
        mid = self._clob.get_midpoint(tid)
        return self._features_from_book(candidate.market_id, tid, book, mid)

    def _features_from_book(
        self,
        market_id: str,
        token_id: str,
        book: OrderBookSnapshot,
        mid: float | None,
    ) -> LiveFeatures:
        bb, ba = book.best_bid, book.best_ask
        spread_abs = None
        spread_bps = book.spread_bps()
        if bb is not None and ba is not None:
            spread_abs = float(ba) - float(bb)

        bid_sz = book.bids[0].size if book.bids else 0.0
        ask_sz = book.asks[0].size if book.asks else 0.0
        m = mid or book.mid()
        depth_usd = (bid_sz + ask_sz) * float(m or 0.0)
        imb = normalize_imbalance(bid_sz, ask_sz)

        hist = self._mid_history[token_id]
        now = time.time()
        hist.append((now, float(m or 0.5)))
        hist[:] = [x for x in hist if now - x[0] <= 60.0]
        mid_change_bps = 0.0
        if len(hist) >= 2 and hist[0][1] > 0:
            mid_change_bps = (hist[-1][1] - hist[0][1]) / hist[0][1] * 10000.0

        response_score = min(1.0, max(0.0, depth_usd / max(self._settings.min_orderbook_depth_usd * 5, 1.0)))

        return LiveFeatures(
            best_bid=bb,
            best_ask=ba,
            spread_abs=spread_abs,
            spread_bps=spread_bps,
            depth_top_usd=depth_usd,
            book_imbalance=imb,
            mid_change_1m_bps=mid_change_bps,
            update_rate_hz=0.0,
            recent_trade_count=0,
            response_score=response_score,
            book=book,
        )
