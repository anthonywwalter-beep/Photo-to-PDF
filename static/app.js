// Upload page (step 3). Plain JavaScript, no build step.
// Privacy: the image is previewed from a local object URL and sent only to /api/extract.
// Text that comes back from a document is only ever inserted as plain text (textContent), never as markup.
(() => {
  const MAX_MB = 5; // matches the server default; the server's answer is the final word
  const $ = (id) => document.getElementById(id);
  const el = {
    drop: $("drop"), file: $("file"), status: $("status"), banner: $("mode-banner"),
    picker: $("picker"), work: $("work"), preview: $("preview"), summary: $("summary"),
    result: $("result"), rawWrap: $("raw-wrap"), raw: $("raw"), another: $("another"),
  };
  let objectUrl = null;
  let controller = null;

  function setStatus(text, kind) {
    el.status.textContent = text;
    el.status.className = kind || "";
  }

  function reset() {
    if (controller) controller.abort();
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = controller = null;
    el.preview.removeAttribute("src");
    el.result.replaceChildren();
    el.summary.textContent = "";
    el.raw.textContent = "";
    el.rawWrap.hidden = el.work.hidden = el.another.hidden = true;
    el.picker.hidden = false;
    setStatus("");
  }

  function renderTable(data) {
    el.result.replaceChildren();
    if (!data.rows.length) {
      el.result.textContent = "No rows were found in this image.";
      return;
    }
    const table = document.createElement("table");
    const head = table.createTHead().insertRow();
    for (const name of data.columns) {
      const th = document.createElement("th");
      th.scope = "col";
      th.textContent = name;
      head.appendChild(th);
    }
    const body = table.createTBody();
    for (const row of data.rows) {
      const tr = body.insertRow();
      for (const cell of row) tr.insertCell().textContent = cell.v;
    }
    el.result.appendChild(table);
  }

  async function errorMessage(res) {
    try {
      const j = await res.json();
      if (typeof j.detail === "string") return j.detail;
    } catch (_) { /* not JSON */ }
    return `Something went wrong (error ${res.status}).`;
  }

  async function handleFile(file) {
    if (!file.type.startsWith("image/")) {
      return setStatus("That is not an image. Use a JPG, PNG, WebP, or GIF.", "error");
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      return setStatus(`That file is larger than ${MAX_MB} MB. Try a smaller photo.`, "error");
    }
    reset();
    objectUrl = URL.createObjectURL(file);
    el.preview.src = objectUrl;
    el.picker.hidden = true;
    el.work.hidden = el.another.hidden = false;
    setStatus("Reading your image. This can take a little while.", "busy");

    controller = new AbortController();
    try {
      const res = await fetch("/api/extract", {
        method: "POST", body: file, headers: { "Content-Type": file.type }, signal: controller.signal,
      });
      if (!res.ok) return setStatus(await errorMessage(res), "error");
      const data = await res.json();
      renderTable(data);
      el.summary.textContent =
        `Layout: ${data.layout} · ${data.rows.length} row(s) · ${data.columns.length} column(s)`;
      el.raw.textContent = JSON.stringify(data, null, 2);
      el.rawWrap.hidden = false;
      setStatus("");
    } catch (err) {
      if (err.name === "AbortError") return;
      setStatus("Could not reach the server. Check that it is running and try again.", "error");
    }
  }

  function pick(files) {
    if (!files || !files.length) return;
    if (files.length > 1) return setStatus("One image at a time for now. Pick a single file.", "error");
    handleFile(files[0]);
  }

  el.drop.addEventListener("click", () => el.file.click());
  el.drop.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); el.file.click(); }
  });
  el.file.addEventListener("change", () => { pick(el.file.files); el.file.value = ""; });
  el.drop.addEventListener("dragover", (e) => { e.preventDefault(); el.drop.classList.add("over"); });
  el.drop.addEventListener("dragleave", () => el.drop.classList.remove("over"));
  el.drop.addEventListener("drop", (e) => {
    e.preventDefault();
    el.drop.classList.remove("over");
    pick(e.dataTransfer && e.dataTransfer.files);
  });
  el.another.addEventListener("click", reset);

  // Tell the user which mode the server is in, so demo data is never mistaken for a real reading.
  fetch("/health").then((r) => r.json()).then((h) => {
    if (h.mode === "demo") {
      el.banner.textContent = "Demo mode: the table you see is sample data. Your image is not read or sent anywhere.";
    } else if (h.mode === "no-key") {
      el.banner.textContent = "No API key is set, so reading is switched off. Set ANTHROPIC_API_KEY, or start the server with DEMO_MODE=1 to try sample data.";
    } else return;
    el.banner.hidden = false;
  }).catch(() => {});
})();
