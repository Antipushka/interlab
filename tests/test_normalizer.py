from interlab.model import PageModel, Style, VectorObject
from interlab.normalizer import normalize


def line(identifier, start, end):
    return VectorObject(identifier, [{"type":"line","p1":start,"p2":end}], Style([0,0,0],None,1), [*start,*end], source_ids=[identifier])


def test_exact_duplicates_and_contiguous_lines_are_safely_reduced():
    model=PageModel(100,100,[line("a",[0,0],[1,0]),line("duplicate",[0,0],[1,0]),line("b",[1,0],[2,0])],[])
    normalized,stats=normalize(model)
    assert len(normalized.vectors)==1
    assert set(normalized.vectors[0].source_ids)=={"a","duplicate","b"}
    assert stats["duplicates_removed"]==1
    assert stats["collinear_merges"]==1


def test_corner_is_not_merged():
    model=PageModel(100,100,[line("a",[0,0],[1,0]),line("b",[1,0],[1,1])],[])
    normalized,_=normalize(model)
    assert len(normalized.vectors)==2

