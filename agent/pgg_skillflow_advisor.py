"""Minimal SkillFlow advisory classifier used by live-window gate.

This module is intentionally conservative: it only provides routing metadata for
ledger rows and never enables route enforcement or answer-chain replacement.
"""
from __future__ import annotations

from typing import Any


def advise(task_text: str) -> dict[str, Any]:
    text = (task_text or '').lower()
    risk_flags: list[str] = []
    if any(x in text for x in ['production', '生产', 'route_enforce', 'answer-chain', 'answer chain']):
        risk_flags.append('production')
    if any(x in text for x in ['legal', '法律', '律师', '案件']):
        risk_flags.append('legal')
    task_class = 'general'
    if any(x in text for x in ['validator', 'gate', '门禁', '校验']):
        task_class = 'gate_validation'
    elif any(x in text for x in ['oss', 'github', '开源']):
        task_class = 'oss_learning'
    return {
        'task_class': task_class,
        'risk_flags': risk_flags,
        'selected_advisory_route': 'skillflow_advisor_primary',
        'policy': {'collapse_risk': False},
    }
