import test from "node:test";
import assert from "node:assert/strict";
import { createApp } from "../src/app.js";

test("health endpoint and static page respond", async () => {
  const server = createApp().listen(0);
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    const h = await fetch(`${base}/health`);
    assert.equal(h.status, 200);
    assert.deepEqual(await h.json(), { ok: true });
    const page = await fetch(`${base}/`);
    assert.equal(page.status, 200);
    assert.match(await page.text(), /Photo to Table/);
  } finally {
    server.close();
  }
});
