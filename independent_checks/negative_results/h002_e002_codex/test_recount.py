"""Boundary checks for frozen decisions and temporal fee selection; no real data."""
import importlib.util
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal as D

spec = importlib.util.spec_from_file_location('independent_recount', Path(__file__).with_name('recount.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def cohort(edge='0.005', count=20, events=5):
    return [{'neg_risk_id': str(i % events), 'scheduled_slot': str(i // events),
             'long_size_ok': True, 'short_size_ok': False,
             'edge_long': D(edge), 'edge_short': D(1)} for i in range(count)]


def test_frozen_minimum_and_strict_edge_threshold():
    assert r.decision(cohort(count=19), ['0','1','2','3'])[0] == 'DATA-BLOCKED'
    assert r.decision(cohort(events=4), ['0','1','2','3','4'])[0] == 'DATA-BLOCKED'
    assert r.decision(cohort(), ['0','1','2','3'])[0] == 'REJECT'
    assert r.decision(cohort('0.0050001'), ['0','1','2','3'])[0] == 'INCONCLUSIVE'


def test_episodes_require_consecutive_scheduled_slots():
    rows = cohort()
    rows[0]['edge_long'] = rows[10]['edge_long'] = D('0.01')
    assert r.decision(rows, ['0','1','2','3'])[0] == 'REJECT'
    rows[5]['edge_long'] = D('0.01')
    assert r.decision(rows, ['0','1','2','3'])[0] == 'INCONCLUSIVE'


def test_fee_has_no_future_lookahead_and_unknown_is_not_free():
    at = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    future = {'observed_at': '2026-08-20T13:00:00Z', 'fees_enabled': 0, 'fee_rate': 0}
    past = {'observed_at': '2026-08-20T11:00:00Z', 'fees_enabled': 1, 'fee_rate': 0.05}
    assert r.fee_rate({}, [future], at) == (None, 'unknown')
    assert r.fee_rate({}, [past,future], at)[0] == D('0.05')
    assert r.fee_rate({'feeSchedule': {'rate': 0.04}}, [future], at)[0] == D('0.04')
    assert r.fee_rate({'feesEnabled': False}, [], at)[0] == 0


def test_tradable_dates_and_placeholder_exhaustiveness_inputs():
    event = {'markets': [
        {'id':'1','question':'Named outcome', 'enableOrderBook':True, 'createdAt':'2026-08-19T00:00:00Z'},
        {'id':'2','question':'Future', 'enableOrderBook':True, 'createdAt':'2026-08-21T00:00:00Z'},
        {'id':'3','question':'Closed', 'enableOrderBook':True, 'createdAt':'2026-08-19T00:00:00Z','closedTime':'2026-08-20T00:00:00Z'},
        {'id':'4','question':'Will Candidate A win?', 'enableOrderBook':True},
        {'id':'5','question':'Other', 'negRiskOther':True, 'enableOrderBook':True, 'createdAt':'2026-08-19T00:00:00Z'},
        {'id':'6','question':'Unknown date', 'enableOrderBook':True}]}
    required, placeholders, unknown, other = r.tradable_legs(event, r.dt('2026-08-20T00:00:00Z'))
    assert (required, placeholders, unknown, other) == (['1','5'], ['4'], ['6'], {'5'})
