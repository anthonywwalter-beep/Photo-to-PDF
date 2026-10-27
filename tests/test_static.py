"""The web page is served, wired up, and keeps its safety rules."""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

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
    html = (STATIC / "index.html").read_text()
    js = (STATIC / "app.js").read_text()
    used = set(re.findall(r'\$\("([\w-]+)"\)', js))
    missing = [i for i in used if f'id="{i}"' not in html]
    assert not missing, f"app.js looks up ids that index.html lacks: {missing}"


def test_script_never_uses_innerhtml():
    """Text from documents must go in with textContent; innerHTML would allow script injection."""
    js = (STATIC / "app.js").read_text()
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js and "document.write" not in js
