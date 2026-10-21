import pytest

from app.extraction import ExtractionError, parse_model_output, sniff_media_type


def test_parses_fenced_json_and_flags():
    text = 'Here you go:\n```json\n{"layout":"table","columns":["A","B"],"rows":[[{"v":"1","low":false},{"v":"2x","low":true}]]}\n```'
    out = parse_model_output(text)
    assert out.layout == "table"
    assert out.columns == ["A", "B"]
    assert [c.v for c in out.rows[0]] == ["1", "2x"]
    assert [c.low for c in out.rows[0]] == [False, True]


def test_short_rows_padded_and_flagged_long_rows_trimmed():
    out = parse_model_output('{"columns":["A","B","C"],"rows":[[{"v":"1"}],[{"v":"1"},{"v":"2"},{"v":"3"},{"v":"4"}]]}')
    assert len(out.rows[0]) == 3 and out.rows[0][1].low and out.rows[0][2].low
    assert len(out.rows[1]) == 3


def test_plain_string_and_null_cells_tolerated():
    out = parse_model_output('{"columns":["A","B"],"rows":[["x",null]]}')
    assert [c.v for c in out.rows[0]] == ["x", ""]


def test_layout_hint_overrides_model_and_bad_layout_defaults():
    assert parse_model_output('{"layout":"table","columns":["A"],"rows":[]}', "form").layout == "form"
    assert parse_model_output('{"layout":"weird","columns":["A"],"rows":[]}').layout == "table"


@pytest.mark.parametrize("bad", ["", "no json here", "{not json}", '{"columns":[],"rows":[]}', "[1,2]"])
def test_bad_output_raises_safe_error(bad):
    with pytest.raises(ExtractionError):
        parse_model_output(bad)


def test_sniff_media_type(png):
    assert sniff_media_type(png) == "image/png"
    assert sniff_media_type(b"\xff\xd8\xff\xe0abc") == "image/jpeg"
    assert sniff_media_type(b"%PDF-1.7") is None
    assert sniff_media_type(b"hello") is None
