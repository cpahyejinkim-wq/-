"""Theme / sector engine.

Top-down: is the theme moving, do peers confirm, and is this stock a leader
or a laggard inside the theme? The PDF treats a chart setup as more
trustworthy when the theme is already in motion with multiple names
breaking out together.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import List

from backend.models.analysis_models import ThemeAnalysis
from backend.models.provider_models import ThemeSnapshot
from backend.models.score_models import ThemeBuckets
from backend.utils.math_utils import clamp, rescale


@dataclass
class ThemeResult:
    buckets: ThemeBuckets
    sector_name: str | None
    theme_name: str | None
    sector_strength: str
    theme_strength: str
    peer_confirmation: str
    peer_names: List[str]
    role_in_theme: str
    comment: str


def analyze(snap: ThemeSnapshot, own_perf_1m: float) -> ThemeResult:
    buckets = ThemeBuckets()
    if not snap.available:
        return ThemeResult(
            buckets=buckets,
            sector_name=None, theme_name=None,
            sector_strength="데이터 없음",
            theme_strength="데이터 없음",
            peer_confirmation="데이터 없음",
            peer_names=[],
            role_in_theme="unknown",
            comment="섹터 / 테마 데이터 미제공 — 0 처리",
        )

    # Sector strength
    sector_perf = snap.sector_perf_1m or 0.0
    buckets.sector_strength = clamp(rescale(sector_perf, -3.0, 12.0, 0.0, 3.0), 0.0, 3.0)
    sector_tag = _strength_label(sector_perf)

    # Theme momentum
    theme_perf = snap.theme_perf_1m or 0.0
    buckets.theme_momentum = clamp(rescale(theme_perf, -3.0, 12.0, 0.0, 3.0), 0.0, 3.0)
    theme_tag = _strength_label(theme_perf)

    # Peer confirmation
    peers = snap.peers or []
    strong_peers = [p for p in peers if p.perf_1m > 3.0]
    peer_conf_ratio = len(strong_peers) / max(1, len(peers))
    buckets.peer_confirmation = clamp(peer_conf_ratio * 2.0, 0.0, 2.0)
    if not peers:
        peer_conf_label = "피어 데이터 없음"
    elif peer_conf_ratio >= 0.7:
        peer_conf_label = f"피어 {len(strong_peers)}/{len(peers)} 동반 강세"
    elif peer_conf_ratio >= 0.4:
        peer_conf_label = f"피어 {len(strong_peers)}/{len(peers)} 부분 동조"
    else:
        peer_conf_label = f"피어 {len(strong_peers)}/{len(peers)} 동반 미약"

    # Leader / follower / isolated
    peer_avg = mean([p.perf_1m for p in peers]) if peers else 0.0
    if peers and own_perf_1m > peer_avg + 3.0 and peer_conf_ratio > 0.3:
        role = "leader"
        buckets.leader_bonus = 2.0
    elif peers and own_perf_1m >= peer_avg - 2.0 and peer_conf_ratio > 0.3:
        role = "follower"
        buckets.leader_bonus = 1.0
    elif peers and peer_conf_ratio < 0.2 and own_perf_1m > peer_avg + 5.0:
        role = "isolated"
        buckets.leader_bonus = 0.3
    elif not peers:
        role = "unknown"
        buckets.leader_bonus = 0.3
    else:
        role = "follower"
        buckets.leader_bonus = 0.5

    comment_parts = [
        f"섹터 {snap.sector_name or '-'} {sector_tag}",
        f"테마 {snap.theme_name or '-'} {theme_tag}",
        peer_conf_label,
        f"테마 내 포지션: {role}",
    ]
    return ThemeResult(
        buckets=buckets,
        sector_name=snap.sector_name,
        theme_name=snap.theme_name,
        sector_strength=f"{sector_tag} ({sector_perf:+.1f}%)",
        theme_strength=f"{theme_tag} ({theme_perf:+.1f}%)",
        peer_confirmation=peer_conf_label,
        peer_names=[p.name for p in peers],
        role_in_theme=role,
        comment=" · ".join(comment_parts),
    )


def _strength_label(perf: float) -> str:
    if perf > 8:
        return "강세"
    if perf > 3:
        return "상승"
    if perf > -1:
        return "중립"
    return "약세"


def to_theme_analysis(result: ThemeResult) -> ThemeAnalysis:
    return ThemeAnalysis(
        score=result.buckets.total(),
        sector_name=result.sector_name,
        theme_name=result.theme_name,
        sector_strength=result.sector_strength,
        theme_strength=result.theme_strength,
        peer_confirmation=result.peer_confirmation,
        peer_names=result.peer_names,
        role_in_theme=result.role_in_theme,  # type: ignore[arg-type]
        comment=result.comment,
    )
