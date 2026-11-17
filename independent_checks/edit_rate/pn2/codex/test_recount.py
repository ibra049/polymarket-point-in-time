import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('recount',Path(__file__).with_name('recount.py'))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_normalization_freeze():
    assert m.normalized('  ＹＥＳ\u00a0\nStraße  ') == m.normalized('yes STRASSE')
    assert m.normalized('one?') != m.normalized('one')


def test_wilson_zero_and_missing_denominator():
    assert m.wilson(0,0) is None
    lo,hi=m.wilson(0,641)
    assert abs(lo)<1e-15 and abs(hi-0.005957214394557545)<1e-14


def test_wilson_known_reference():
    lo,hi=m.wilson(50,100)
    assert abs(lo-0.4038315304)<1e-9
    assert abs(hi-0.5961684696)<1e-9


def test_deadline_offsets_and_exact_hour_boundary():
    assert (m.instant('2026-01-01T01:00:00Z')-m.instant('2025-12-31T19:00:00-05:00')).total_seconds()==3600


def test_event_clusters_keep_market_multiplicity():
    result=m.metric([{'event_id':'a','category':'x','v':True},
                     {'event_id':'a','category':'x','v':True},
                     {'event_id':'b','category':'x','v':False},
                     {'event_id':'c','category':'y','v':None}],'v')
    assert (result['k'],result['n'],result['eligible_events'],result['positive_events'])==(2,3,2,1)
    assert result['event_cluster_bootstrap_95']==[0.,1.]
