"""The web page is served, wired up, and keeps its safety rules."""
import re
from pathlib import Path
from typing import get_args

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas import LayoutChoice

STATIC = Path(__file__).resolve().parent.parent / "static"
client = TestClient(create_app(Settings()))


def test_page_and_assets_are_served():
    page = client.get("/")
    assert page.status_code == 200
    for asset in ("/static/style.css", "/static/app.js"):
        assert asset in page.text
        assert client.get(asset).status_code == 200


def test_page_states_the_privacy_promise():
    assert "Nothing is stored" in client.get("/").text


def test_page_has_every_element_the_script_uses():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    used = set(re.findall(r'\$\("([\w-]+)"\)', js))
    missing = [i for i in used if f'id="{i}"' not in html]
    assert not missing, f"app.js looks up ids that index.html lacks: {missing}"


def test_script_never_uses_innerhtml():
    """Text from documents must go in with textContent; innerHTML would allow script injection."""
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js and "document.write" not in js


def test_script_never_stores_anything_in_the_browser():
    """Nothing-stored promise: no localStorage, sessionStorage, IndexedDB, or cookies."""
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    for banned in ("localStorage", "sessionStorage", "indexedDB", "document.cookie"):
        assert banned not in js, banned


def test_layout_toggle_offers_exactly_the_layouts_the_api_accepts():
    """If the API gains or loses a layout, the page's toggle must change with it."""
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    offered = re.findall(r'name="layout" value="(\w+)"', html)
    assert sorted(offered) == sorted(get_args(LayoutChoice))


def test_file_picker_accepts_several_images():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert re.search(r'<input id="file"[^>]*\bmultiple\b', html)
