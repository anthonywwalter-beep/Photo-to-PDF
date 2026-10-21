"""The real extractor, driven by a fake client. No network, no key."""
import base64
from types import SimpleNamespace

import pytest

from app.extraction import AnthropicExtractor, ExtractionError

REPLY = '{"layout":"form","columns":["Name"],"rows":[[{"v":"Sam","low":false}]]}'


class FakeClient:
    def __init__(self, reply=REPLY, boom=None):
        self.calls, self._reply, self._boom = [], reply, boom
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        if self._boom:
            raise self._boom
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self._reply)])


def test_sends_image_and_prompt_and_parses(png):
    fake = FakeClient()
    out = AnthropicExtractor(model="m", client=fake).extract(png, "image/png", "form")
    call = fake.calls[0]
    assert call["model"] == "m"
    image_block, text_block = call["messages"][0]["content"]
    assert image_block["source"]["media_type"] == "image/png"
    assert base64.b64decode(image_block["source"]["data"]) == png
    assert "FORM" in text_block["text"]
    assert out.layout == "form" and out.rows[0][0].v == "Sam"


def test_auto_prompt_asks_model_to_choose(png):
    fake = FakeClient()
    AnthropicExtractor(client=fake).extract(png, "image/png", "auto")
    assert "First decide the layout" in fake.calls[0]["messages"][0]["content"][1]["text"]


def test_api_failure_becomes_safe_error(png):
    with pytest.raises(ExtractionError) as e:
        AnthropicExtractor(client=FakeClient(boom=RuntimeError("secret-api-detail"))).extract(png, "image/png", "auto")
    assert "secret-api-detail" not in str(e.value)
