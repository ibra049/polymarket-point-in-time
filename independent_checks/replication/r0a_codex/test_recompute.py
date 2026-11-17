"""Offline arithmetic and differential checks; no released-data reads."""
from datetime import datetime, timezone
import math
import random
import hashlib
import os

import numpy as np
import pyarrow as pa
import pytest

from recompute import COLUMNS, STAGES, measure_batch, verified_bytes
from diagnose_null_market import classify


LOOKUPS = {"multi": pa.array(["multi"], type=pa.large_string()),
           "markets": pa.array(["binary", "multi"], type=pa.large_string()),
           "high": pa.array(["high"], type=pa.large_string()),
           "known": pa.array(["low", "other", "high"], type=pa.large_string())}


def row(**kw):
    value = dict(timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                 market_id="binary", price=0.9, quantity=10.,
                 maker_address="other", taker_address="low",
                 taker_bought=True, winner=True)
    value.update(kw)
    return value


def batch(rows):
    types = {"timestamp": pa.timestamp("ns", tz="UTC"), "price": pa.float64(),
             "quantity": pa.float64(), "taker_bought": pa.bool_(), "winner": pa.bool_()}
    return pa.record_batch([pa.array([r[c] for r in rows], type=types.get(c, pa.large_string()))
                            for c in COLUMNS], names=COLUMNS)


def test_hand_calculation_roles_weights_and_boundary():
    rows = [row(), row(price=1., quantity=2., winner=False),
            row(taker_bought=False, price=.95, quantity=20.),
            row(price=np.nextafter(.9, 0.)),
            row(taker_bought=False, taker_address="high", quantity=5.)]
    stages, diagnostics, groups, _ = measure_batch(batch(rows), LOOKUPS)
    assert stages["return_sample"] == 5
    assert diagnostics["binary_unknown_buyer_hhi"] == 0
    assert groups["taker"]["purchases"] == 2
    assert groups["taker"]["cost"] == 11
    assert groups["taker"]["gain"] == -1
    # A high-HHI seller does not disqualify a low-HHI maker buyer.
    assert groups["maker"]["purchases"] == 2
    assert groups["maker"]["cost"] == 23.5
    assert groups["maker"]["gain"] == pytest.approx(1.5)


def test_filters_against_separate_scalar_oracle():
    rng = random.Random(20261116)
    rows = [row(market_id=rng.choice(["binary", "multi", "unknown", None]),
                price=rng.choice([None, float("nan"), float("inf"), 0., -.1, .1, .899999999, .9, 1., 1.1]),
                quantity=rng.choice([None, -1., 0., 2., 100., float("inf")]),
                maker_address=rng.choice([None, "low", "other", "high", "unknown"]),
                taker_address=rng.choice([None, "low", "other", "high", "unknown"]),
                taker_bought=rng.choice([None, True, False]),
                winner=rng.choice([None, True, False])) for _ in range(2000)]
    expected = dict.fromkeys(STAGES, 0)
    amounts = {role: {k: [] for k in ["cost", "payoff", "gain"]} for role in ["maker", "taker"]}
    counts = {"maker": 0, "taker": 0}
    for r in rows:
        expected["observed"] += 1
        if any(r[k] is None for k in ["maker_address", "taker_address", "taker_bought", "price", "quantity"]):
            continue
        if r["maker_address"] == r["taker_address"]:
            continue
        expected["complete_distinct"] += 1
        p, q = r["price"], r["quantity"]
        if not (math.isfinite(p) and math.isfinite(q) and 0 < p <= 1 and q > 0):
            continue
        expected["valid_price_quantity"] += 1
        if r["market_id"] == "multi":
            continue
        expected["two_outcome"] += 1
        buyer = r["taker_address"] if r["taker_bought"] else r["maker_address"]
        if buyer == "high":
            continue
        expected["buyer_hhi"] += 1
        if r["winner"] is None:
            continue
        expected["return_sample"] += 1
        if p < .9:
            continue
        role = "taker" if r["taker_bought"] else "maker"
        counts[role] += 1
        amounts[role]["cost"].append(p*q)
        amounts[role]["payoff"].append(int(r["winner"])*q)
        amounts[role]["gain"].append((int(r["winner"])-p)*q)
    stages, diagnostics, groups, _ = measure_batch(batch(rows), LOOKUPS)
    assert stages == expected
    assert diagnostics["valid_unknown_market"] > 0
    assert diagnostics["binary_unknown_buyer_hhi"] > 0
    for role in counts:
        assert groups[role]["purchases"] == counts[role]
        for key, values in amounts[role].items():
            assert groups[role][key] == pytest.approx(math.fsum(values))


def test_manifest_bytes_survive_mtime_drift_and_reject_content_change(tmp_path):
    path = tmp_path / "input"
    original = b"frozen input bytes"
    path.write_bytes(original)
    digest = hashlib.sha256(original).hexdigest()
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns - 64))
    # The old stat-equality rule rejects this same-content input.
    assert path.stat().st_mtime_ns != stat.st_mtime_ns
    frozen = verified_bytes(path, digest, len(original))
    assert frozen == original
    # Already loaded bytes are immutable even if the pathname later changes.
    path.write_bytes(b"different content")
    assert frozen == original
    with pytest.raises(ValueError, match="manifest content mismatch"):
        verified_bytes(path, digest, len(original))


def test_null_market_diagnostic_preserves_unknown_tokens():
    rows = pa.table({"prediction_id": ["known", "orphan", "orphan"],
                     "taker_bought": [True, True, False],
                     "maker_address": ["low", "low", "high"],
                     "taker_address": ["low", "low", "low"],
                     "winner": pa.array([True, None, None], type=pa.bool_())})
    predictions = pa.table({"prediction_id": ["known"]})
    result = classify(rows, predictions, pa.array(["high"]))
    assert result == {"rows": 3, "null_prediction_id": 0,
                      "matched_prediction_id": 1, "unmatched_prediction_id": 2,
                      "known_payoff_rows": 1, "high_hhi_buyer_rows": 1,
                      "after_hhi_rows": 2, "after_hhi_known_payoff_rows": 1}
