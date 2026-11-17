import importlib.util
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).parent))
spec=importlib.util.spec_from_file_location('spotcheck',Path(__file__).with_name('spotcheck.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_abi_dynamic_bytes_and_bounds():
    body=(32).to_bytes(32,'big')+(3).to_bytes(32,'big')+b'abc'+b'\0'*29
    assert m.dynamic_bytes('0x'+body.hex())==b'abc'
    import pytest
    with pytest.raises(ValueError,match='truncated'):
        m.dynamic_bytes('0x'+body[:65].hex())


def test_title_preserves_internal_punctuation():
    assert m.title_and_rules('q: title: Will A, B win?, description: Resolves on X')==('Will A, B win?',' Resolves on X')
    assert m.title_and_rules('title: Other title description:Rules')==('Other title','Rules')


def test_rpc_error_stops_further_network_calls(monkeypatch):
    import pytest
    calls=[]
    def fail(method,params):
        calls.append(method)
        raise RuntimeError('429 quota')
    monkeypatch.setattr(m,'FAILURE',None)
    monkeypatch.setattr(m,'LAST_REQUEST',0.)
    monkeypatch.setattr(m,'_rpc',fail)
    with pytest.raises(RuntimeError,match='429 quota'):m.rpc('eth_getLogs',[])
    with pytest.raises(RuntimeError,match='circuit stopped'):m.rpc('eth_getLogs',[])
    assert calls==['eth_getLogs']


def test_embedded_json_error_with_curl_success_is_failure(monkeypatch,tmp_path):
    import pytest
    from types import SimpleNamespace
    monkeypatch.setattr(m,'HERE',tmp_path)
    monkeypatch.setattr(m.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=0,stdout='{"statusCode":429,"message":"quota"}',stderr=''))
    with pytest.raises(RuntimeError,match='429'):m._rpc('eth_getLogs',[])
    assert '"statusCode": 429' in (tmp_path/'polygon_rpc.jsonl').read_text()
