"""
Sympathetic noise post-processing filter.
Must be applied to ALL model outputs before any scoring.
"""

import json
import re

SYMPATHETIC_CODES = {
    "HEARTBEAT_TIMEOUT", "KEEPALIVE_FAIL", "KEEPALIVE_TIMEOUT",
    "SECONDARY_ALARM", "CASCADING_FAILURE", "PFCP_HEARTBEAT_TIMEOUT",
    "N2_HEARTBEAT_TIMEOUT", "N11_HEARTBEAT_TIMEOUT", "TIMER_EXPIRY",
    "RETRANSMISSION", "DUPLICATE_NAS", "SPURIOUS_MEASUREMENT",
    "BEAM_FAILURE_RECOVERY", "RLC_RETRANSMISSION", "HARQ_NACK",
}

VALID_ROOT_CAUSES = {
    "core_network_failure", "authentication_failure", "normal",
    "handover_failure", "congestion", "qos_violation",
    "transport_jitter", "radio_failure",
}


def filter_sympathetic_noise(predicted_codes: list) -> list:
    """Remove sympathetic noise codes; keep only valid root cause labels."""
    seen, filtered = set(), []
    for code in predicted_codes:
        if not isinstance(code, str):
            continue
        norm = code.strip().lower()
        if code.strip().upper() in SYMPATHETIC_CODES:
            continue
        if norm in VALID_ROOT_CAUSES and norm not in seen:
            seen.add(norm)
            filtered.append(norm)
    return filtered if filtered else ["normal"]


def extract_root_cause_from_text(text: str) -> list:
    """Parse root cause labels from free-form model output text."""
    match = re.search(r'\[.*?\]', text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, list):
                return filter_sympathetic_noise(parsed)
        except json.JSONDecodeError:
            pass
    found = [label for label in VALID_ROOT_CAUSES if label in text.lower()]
    return filter_sympathetic_noise(found) if found else ["normal"]
