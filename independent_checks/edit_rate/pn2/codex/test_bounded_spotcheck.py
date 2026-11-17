import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from bounded_spotcheck import ranges


def test_pocket_ranges_cover_original_history_without_exceeding_cap():
    chunks=ranges(58008243,97166757)
    assert len(chunks)==784
    assert chunks[0][0]==58008243 and chunks[-1][1]==97166757
    assert all(0<hi-lo+1<=50000 for lo,hi in chunks)
    assert all(left[1]+1==right[0] for left,right in zip(chunks,chunks[1:]))
    assert sum(hi-lo+1 for lo,hi in chunks)==97166757-58008243+1


def test_exact_cap_and_single_block():
    assert ranges(7,7)==[(7,7)]
    assert ranges(7,50006)==[(7,50006)]
    assert ranges(7,50007)==[(7,50006),(50007,50007)]


def test_source_specific_widths_cover_same_interval():
    for width,expected in [(10000,3916),(1000000,40)]:
        chunks=ranges(58008243,97166757,width)
        assert len(chunks)==expected
        assert all(hi-lo+1<=width for lo,hi in chunks)
        assert sum(hi-lo+1 for lo,hi in chunks)==97166757-58008243+1
