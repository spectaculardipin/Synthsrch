from synthsrch.providers.base import SearchResult, apply_keyword_filter, slice_rank


def _r(i, title, snippet=""):
    return SearchResult(id=f"x-{i}", title=title, url=f"https://example.com/{i}", publisher="example.com", rank=i, snippet=snippet)


def test_keyword_any_is_union():
    rs = [_r(1, "apple pie recipe"), _r(2, "banana bread"), _r(3, "cherry tart apple")]
    out = apply_keyword_filter(rs, ["apple", "banana"], "ANY")
    assert {r.rank for r in out} == {1, 2, 3}


def test_keyword_all_is_intersection():
    rs = [_r(1, "apple pie recipe"), _r(2, "banana bread"), _r(3, "cherry tart apple", "banana mix")]
    out = apply_keyword_filter(rs, ["apple", "banana"], "ALL")
    assert [r.rank for r in out] == [3]


def test_slice_rank_renumbers():
    rs = [_r(i, f"t{i}") for i in range(1, 50)]
    chunk = slice_rank(rs, 20, 40)
    assert len(chunk) == 21
    assert chunk[0].rank == 20 and chunk[-1].rank == 40
