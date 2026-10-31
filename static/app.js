// Upload, review, and edit page (steps 3-7). Plain JavaScript, no build step.
// Privacy: images are previewed from local object URLs and sent only to /api/extract, one request per image.
// Edits and the CSV are built in this browser tab and never sent anywhere; closing the tab discards them.
// Text that comes back from a document (and file names) is only ever inserted as plain text or as input
// values, never as markup.
(() => {
  const MAX_MB = 5;        // matches the server default; the server's answer is the final word
  const MAX_FILES = 20;    // bounds cost and memory for one batch
  const CONCURRENCY = 3;   // images read at the same time
  const $ = (id) => document.getElementById(id);
  const el = {
    drop: $("drop"), file: $("file"), status: $("status"), banner: $("mode-banner"),
    picker: $("picker"), work: $("work"), preview: $("preview"), summary: $("summary"),
    result: $("result"), rawWrap: $("raw-wrap"), raw: $("raw"), another: $("another"),
    tools: $("tools"), addRow: $("add-row"), download: $("download"),
    nextFlag: $("next-flag"), flagCount: $("flag-count"), layout: $("layout"),
    undo: $("undo"), undoText: $("undo-text"), undoBtn: $("undo-btn"),
    tabs: $("tabs"), addMore: $("add-more"), issues: $("issues"), srcOpt: $("src-opt"), srcCol: $("src-col"),
  };
  let files = [];        // { file, name, url, status: queued|reading|done|error, error, layout }
  let current = 0;       // index of the image shown in the Original pane
  let state = null;      // { columns: [name], keys: [matching key], rows: [{ src, cells: [{ v, low }] }] }
  let rawBy = {};        // as-read answers, by file index
  let dirty = false;     // edits not yet downloaded
  let undoInfo = null;   // the last deleted row, so it can be restored
  let flagCursor = null; // the flagged cell the user was last taken to
  let layoutChoice = "auto"; // what the user asked for: auto, table, form, or list
  let readId = 0;        // identifies this session, so answers that arrive after "start over" are ignored
  let reading = 0;       // images currently waiting for an answer
  let controller = null;
  let skippedNote = "";

  // ---------- CSV ----------
  // Spreadsheets run cells that start with = + - @ (or tab/CR) as formulas. Document text is untrusted,
  // so such cells get a leading apostrophe. Plain numbers and phone numbers like -5.00 or +1 (555) 014-2 are left alone.
  function neutralize(v) {
    if (/^[=@\t\r]/.test(v)) return "'" + v;
    if (/^[+-]/.test(v) && !/^[+-][\d.,\s()$€£%-]*$/.test(v)) return "'" + v;
    return v;
  }
  function csvField(v) {
    v = neutralize(v);
    return /[",\r\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
  }
  function toCsv(columns, rows, sources) {
    const head = sources ? [...columns, "Source image"] : columns;
    const body = rows.map((r) => {
      const v = r.cells.map((c) => c.v);
      if (sources) v.push(sources[r.src] || "");
      return v;
    });
    return [head, ...body].map((l) => l.map(csvField).join(",")).join("\r\n") + "\r\n";
  }
  function downloadCsv() {
    const sources = files.length > 1 && el.srcCol.checked ? files.map((f) => f.name) : null;
    // The BOM makes Excel read accents and non-English text correctly.
    const blob = new Blob(["\ufeff" + toCsv(state.columns, state.rows, sources)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "extracted-table.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    dirty = false;
    const left = countFlags();
    setStatus("Downloaded extracted-table.csv." +
      (left ? ` Note: ${left} flagged cell${left === 1 ? " was" : "s were"} not checked.` : ""));
  }

  // ---------- state and status ----------
  function setStatus(text, kind) {
    el.status.textContent = text;
    el.status.className = kind || "";
  }
  function clearUndo() { undoInfo = null; el.undo.hidden = true; }
  function confirmDiscard(message) {
    return !dirty || window.confirm(message || "You have edits that have not been downloaded. Discard them?");
  }
  const layoutRadios = () => [...el.layout.querySelectorAll("input")];
  function selectLayout(value) { layoutRadios().forEach((r) => { r.checked = r.value === value; }); }
  function setLayoutEnabled(on) { layoutRadios().forEach((r) => { r.disabled = !on; }); }
  function updateBusy() {
    setLayoutEnabled(reading === 0);
    el.addMore.disabled = reading > 0;
  }
  function progressText(total, finished) {
    return total === 1 ? "Reading your image. This can take a little while."
      : `Reading images: ${finished} of ${total} done. This can take a little while.`;
  }
  function updateSummary() {
    const done = files.filter((f) => f.status === "done");
    let label;
    if (layoutChoice === "auto") {
      const counts = {};
      done.forEach((f) => { counts[f.layout] = (counts[f.layout] || 0) + 1; });
      label = "Detected layout: " + Object.entries(counts).map(([k, n]) => (done.length > 1 ? `${k} (${n})` : k)).join(", ");
    } else {
      label = `Layout (your choice): ${layoutChoice}`;
    }
    const images = files.length > 1 ? ` · ${done.length} of ${files.length} images` : "";
    el.summary.textContent = `${label}${images} · ${state.rows.length} row(s) · ${state.columns.length} column(s)`;
  }

  function reset() {
    readId++;
    if (controller) controller.abort();
    controller = null;
    files.forEach((f) => URL.revokeObjectURL(f.url));
    files = []; rawBy = {}; state = null; current = 0; reading = 0; skippedNote = "";
    layoutChoice = "auto";
    selectLayout("auto");
    setLayoutEnabled(true);
    el.addMore.disabled = false;
    el.result.classList.remove("stale");
    dirty = false;
    flagCursor = null;
    clearUndo();
    el.preview.removeAttribute("src");
    el.result.replaceChildren();
    el.issues.replaceChildren();
    el.tabs.replaceChildren();
    el.tabs.hidden = true;
    el.summary.textContent = "";
    el.raw.textContent = "";
    el.rawWrap.hidden = el.tools.hidden = el.work.hidden = el.another.hidden = true;
    el.picker.hidden = false;
    setStatus("");
  }

  // ---------- the images (Original pane) ----------
  function showImage(i) {
    if (!files[i]) return;
    current = i;
    el.preview.src = files[i].url;
    el.preview.alt = files.length > 1 ? `Image ${i + 1} of ${files.length}: ${files[i].name}` : "The image you uploaded";
    renderTabs();
  }
  function renderTabs() {
    el.tabs.replaceChildren();
    el.tabs.hidden = files.length < 2;
    files.forEach((f, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "tab";
      b.textContent = `${i + 1}. ${f.name}${f.status === "reading" ? " …" : f.status === "error" ? " ⚠" : ""}`;
      b.title = f.name;
      const note = f.status === "error" ? ", failed to read" : f.status === "reading" ? ", reading" : "";
      b.setAttribute("aria-label", `Image ${i + 1}, ${f.name}${note}`);
      if (i === current) b.setAttribute("aria-current", "true");
      b.addEventListener("click", () => showImage(i));
      el.tabs.appendChild(b);
    });
  }
  function renderIssues() {
    el.issues.replaceChildren();
    files.forEach((f, i) => {
      if (f.status !== "error") return;
      const p = document.createElement("p");
      p.className = "issue";
      p.append(document.createTextNode(`${files.length > 1 ? f.name + ": " : ""}${f.error} `));
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = "Try again";
      b.addEventListener("click", () => readNew([i]));
      p.appendChild(b);
      el.issues.appendChild(p);
    });
  }

  // ---------- uncertain-cell flags ----------
  // A cell is flagged when the reader was unsure (messy handwriting, blur, a guess). It is cleared only when
  // the user edits it or presses the check mark, never just because they looked at it.
  function countFlags() {
    return state ? state.rows.reduce((n, row) => n + row.cells.filter((c) => c.low).length, 0) : 0;
  }
  function updateFlags() {
    const n = countFlags();
    el.flagCount.textContent = n ? `${n} cell${n === 1 ? "" : "s"} to check` : "No cells flagged";
    el.nextFlag.disabled = n === 0;
  }
  function goToNextFlag() {
    const flagged = [...el.result.querySelectorAll("td.flag textarea")];
    if (!flagged.length) return;
    const after = flagged.find((t) => flagCursor && flagCursor.isConnected &&
      (flagCursor.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING));
    flagCursor = after || flagged[0]; // wraps back to the first
    flagCursor.focus();
    if (flagCursor.scrollIntoView) flagCursor.scrollIntoView({ block: "center" });
  }

  // ---------- merging ----------
  // Columns are matched by name (ignoring case and spacing), so the same field on every page lands in one
  // column. The match key is fixed when the column is created, so renaming a column later does not break it.
  // Rows stay in image order however the answers arrive. Re-ingesting an image replaces that image's rows.
  function ingest(i, data) {
    if (!state) state = { columns: [], keys: [], rows: [] };
    state.rows = state.rows.filter((r) => r.src !== i);
    const used = new Set();
    const map = data.columns.map((name) => {
      const base = name.trim().toLowerCase();
      let key = base, n = 1, k = state.keys.indexOf(key);
      while (k >= 0 && used.has(k)) { key = `${base}\u0000${++n}`; k = state.keys.indexOf(key); } // same name twice on one page
      if (k < 0) {
        k = state.keys.length;
        state.keys.push(key);
        state.columns.push(name);
        state.rows.forEach((r) => r.cells.push({ v: "", low: false }));
      }
      used.add(k);
      return k;
    });
    const fresh = data.rows.map((r) => {
      const cells = state.columns.map(() => ({ v: "", low: false }));
      r.forEach((c, j) => { cells[map[j]] = { v: c.v, low: !!c.low }; });
      return { src: i, cells };
    });
    let at = 0;
    state.rows.forEach((r, idx) => { if (r.src < i) at = idx + 1; });
    state.rows.splice(at, 0, ...fresh);
  }

  // ---------- editable table ----------
  function autosize(ta) {
    ta.style.height = "auto";
    if (ta.scrollHeight) ta.style.height = ta.scrollHeight + "px";
  }

  function buildRow(row, r, showSrc) {
    const tr = document.createElement("tr");
    tr.addEventListener("focusin", () => { if (row.src !== current) showImage(row.src); });
    if (showSrc) {
      const td = tr.insertCell();
      td.className = "srcno";
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = String(row.src + 1);
      b.title = `Show image ${row.src + 1}: ${files[row.src] ? files[row.src].name : ""}`;
      b.setAttribute("aria-label", `Show source image ${row.src + 1}`);
      b.addEventListener("click", () => showImage(row.src));
      td.appendChild(b);
    }
    row.cells.forEach((cell, c) => {
      const td = tr.insertCell();
      const ta = document.createElement("textarea");
      ta._row = row;
      ta._c = c;
      ta.rows = 1;
      ta.value = cell.v;
      const mark = document.createElement("button");
      mark.type = "button";
      mark.className = "mark";
      mark.textContent = "✓";
      mark.title = "Looks right: clear this flag";
      mark.setAttribute("aria-label", `Mark row ${r + 1}, column ${c + 1} as correct`);
      const sync = () => {
        td.classList.toggle("flag", cell.low);
        td.title = cell.low ? "The reader was unsure about this cell. Please check it." : "";
        mark.hidden = !cell.low;
        ta.setAttribute("aria-label", `Row ${r + 1}, column ${c + 1}${cell.low ? ", uncertain, please check" : ""}`);
      };
      const clearFlag = () => { if (cell.low) { cell.low = false; sync(); updateFlags(); } };
      sync();
      ta.addEventListener("input", () => { cell.v = ta.value; autosize(ta); dirty = true; clearFlag(); });
      mark.addEventListener("click", () => { dirty = true; clearFlag(); ta.focus(); });
      ta.addEventListener("keydown", (e) => {
        // Enter moves down a row, like a spreadsheet. Shift+Enter makes a new line inside the cell.
        if (e.key !== "Enter" || e.shiftKey) return;
        e.preventDefault();
        const next = tr.nextElementSibling;
        if (next) next.querySelectorAll("textarea")[c].focus();
      });
      td.append(ta, mark);
    });
    const act = tr.insertCell();
    act.className = "act";
    const del = document.createElement("button");
    del.type = "button";
    del.textContent = "×";
    del.title = `Delete row ${r + 1}`;
    del.setAttribute("aria-label", `Delete row ${r + 1}`);
    del.addEventListener("click", () => deleteRow(row));
    act.appendChild(del);
    return tr;
  }

  function renderTable() {
    // Results can arrive while the user is typing, so remember where they were and put the cursor back.
    const a = document.activeElement;
    const keep = a && el.result.contains(a) ? { row: a._row, c: a._c, h: a._h, s: a.selectionStart, e: a.selectionEnd } : null;
    const showSrc = files.length > 1;
    el.result.replaceChildren();
    const table = document.createElement("table");
    const head = table.createTHead().insertRow();
    if (showSrc) {
      const th = document.createElement("th");
      th.className = "srcno";
      th.scope = "col";
      th.textContent = "Img";
      th.title = "Source image";
      head.appendChild(th);
    }
    state.columns.forEach((name, c) => {
      const input = document.createElement("input");
      input.type = "text";
      input.value = name;
      input._h = c;
      input.setAttribute("aria-label", `Column ${c + 1} name`);
      input.addEventListener("input", () => { state.columns[c] = input.value; dirty = true; });
      const th = document.createElement("th");
      th.scope = "col";
      th.appendChild(input);
      head.appendChild(th);
    });
    head.appendChild(document.createElement("th"));
    const body = table.createTBody();
    state.rows.forEach((row, r) => body.appendChild(buildRow(row, r, showSrc)));
    el.result.appendChild(table);
    if (!state.rows.length) {
      const hint = document.createElement("p");
      hint.className = "hint";
      hint.textContent = "No rows. Use “Add row” to start one.";
      el.result.appendChild(hint);
    }
    flagCursor = null;
    updateSummary();
    updateFlags();
    if (keep) {
      const target = keep.row
        ? [...el.result.querySelectorAll("tbody textarea")].find((t) => t._row === keep.row && t._c === keep.c)
        : el.result.querySelectorAll("thead input")[keep.h];
      if (target) {
        target.focus();
        if (keep.s != null && target.setSelectionRange) target.setSelectionRange(keep.s, keep.e);
      }
    }
    if (window.requestAnimationFrame) {
      requestAnimationFrame(() => el.result.querySelectorAll("textarea").forEach(autosize));
    }
  }

  function updateRaw() {
    const shown = files.length === 1 ? rawBy[0] : files.map((f, i) => ({ file: f.name, result: rawBy[i] || null }));
    el.raw.textContent = JSON.stringify(shown || null, null, 2);
    el.rawWrap.hidden = false;
  }
  function renderAll() {
    renderTabs();
    renderIssues();
    el.srcOpt.hidden = files.length < 2;
    if (state) {
      renderTable();
      el.tools.hidden = false;
      updateRaw();
    }
  }

  function addRow() {
    clearUndo();
    state.rows.push({ src: Math.min(current, files.length - 1), cells: state.columns.map(() => ({ v: "", low: false })) });
    dirty = true;
    renderTable();
    const rows = el.result.querySelectorAll("tbody tr");
    rows[rows.length - 1].querySelector("textarea").focus();
  }

  function deleteRow(row) {
    const index = state.rows.indexOf(row);
    if (index < 0) return;
    state.rows.splice(index, 1);
    undoInfo = { row, index };
    el.undoText.textContent = "Row deleted.";
    el.undo.hidden = false;
    dirty = true;
    renderTable();
  }

  function undoDelete() {
    if (!undoInfo) return;
    state.rows.splice(Math.min(undoInfo.index, state.rows.length), 0, undoInfo.row);
    clearUndo();
    renderTable();
  }

  // ---------- reading images ----------
  async function errorMessage(res) {
    try {
      const j = await res.json();
      if (typeof j.detail === "string") return j.detail;
    } catch (_) { /* not JSON */ }
    return `Something went wrong (error ${res.status}).`;
  }

  async function fetchOne(i, choice) {
    const f = files[i];
    let res;
    try {
      res = await fetch(`/api/extract?layout=${encodeURIComponent(choice)}`, {
        method: "POST", body: f.file, headers: { "Content-Type": f.file.type }, signal: controller.signal,
      });
    } catch (err) {
      if (err.name === "AbortError") throw err;
      throw new Error("Could not reach the server. Check that it is running and try again.");
    }
    if (!res.ok) throw new Error(await errorMessage(res));
    return res.json();
  }

  async function pool(items, worker) {
    const queue = items.slice();
    const runner = async () => { while (queue.length) await worker(queue.shift()); };
    await Promise.all(Array.from({ length: Math.min(CONCURRENCY, queue.length) }, runner));
  }

  // Read some images and add their rows as the answers arrive. Used for new images and for "Try again".
  async function readNew(indices) {
    const session = readId;
    let finished = 0;
    reading += indices.length;
    indices.forEach((i) => { files[i].status = "reading"; files[i].error = null; });
    renderAll();
    updateBusy();
    setStatus(progressText(indices.length, 0), "busy");
    await pool(indices, async (i) => {
      try {
        const data = await fetchOne(i, layoutChoice);
        if (session !== readId) return;
        ingest(i, data);
        rawBy[i] = data;
        files[i].status = "done";
        files[i].layout = data.layout;
      } catch (err) {
        if (err.name === "AbortError" || session !== readId) return;
        files[i].status = "error";
        files[i].error = err.message;
      }
      finished++;
      reading--;
      renderAll();
      updateBusy();
      if (reading > 0) setStatus(progressText(indices.length, finished), "busy");
      else { setStatus(skippedNote); skippedNote = ""; }
    });
  }

  // Read every image again with another layout. Nothing changes on screen until the answers are in,
  // and if every image fails the table already on screen is kept.
  async function rereadAll(choice) {
    const session = readId, previous = layoutChoice, n = files.length;
    const before = files.map((f) => ({ status: f.status, error: f.error, layout: f.layout }));
    const results = new Array(n), errors = new Array(n);
    let finished = 0;
    reading += n;
    files.forEach((f) => { f.status = "reading"; f.error = null; });
    el.result.classList.add("stale");
    renderTabs();
    renderIssues();
    updateBusy();
    setStatus(progressText(n, 0), "busy");
    await pool([...Array(n).keys()], async (i) => {
      try {
        results[i] = await fetchOne(i, choice);
      } catch (err) {
        if (err.name === "AbortError" || session !== readId) return;
        errors[i] = err.message;
      }
      if (session !== readId) return;
      finished++;
      reading--;
      updateBusy();
      if (reading > 0) setStatus(progressText(n, finished), "busy");
    });
    if (session !== readId) return;
    el.result.classList.remove("stale");
    if (!results.some(Boolean)) {
      files.forEach((f, i) => Object.assign(f, before[i]));
      selectLayout(previous);
      renderAll();
      updateBusy();
      return setStatus(errors.find(Boolean) || "Could not read the images.", "error");
    }
    state = null;
    rawBy = {};
    files.forEach((f, i) => {
      if (results[i]) { ingest(i, results[i]); rawBy[i] = results[i]; f.status = "done"; f.layout = results[i].layout; }
      else { f.status = "error"; f.error = errors[i]; }
    });
    layoutChoice = choice;
    selectLayout(choice);
    dirty = false;
    clearUndo();
    renderAll();
    updateBusy();
    setStatus("");
  }

  function addFiles(list) {
    if (reading > 0) return setStatus("Please wait until the current reading has finished.", "error");
    const problem = (f) => !f.type.startsWith("image/") ? "not an image" : f.size > MAX_MB * 1024 * 1024 ? `over ${MAX_MB} MB` : null;
    if (list.length === 1 && problem(list[0])) {
      return setStatus(problem(list[0]) === "not an image"
        ? "That is not an image. Use a JPG, PNG, WebP, or GIF."
        : `That file is larger than ${MAX_MB} MB. Try a smaller photo.`, "error");
    }
    const valid = [], skipped = [];
    for (const f of list) {
      const p = problem(f);
      if (p) skipped.push(`${f.name} (${p})`); else valid.push(f);
    }
    const room = MAX_FILES - files.length;
    valid.slice(Math.max(room, 0)).forEach((f) => skipped.push(`${f.name} (limit of ${MAX_FILES} images)`));
    valid.length = Math.min(valid.length, Math.max(room, 0));
    if (!valid.length) return setStatus(skipped.length ? `Skipped: ${skipped.join(", ")}.` : "No images were chosen.", "error");
    skippedNote = skipped.length ? `Skipped: ${skipped.join(", ")}.` : "";
    const first = files.length;
    if (!controller) controller = new AbortController();
    valid.forEach((f) => files.push({ file: f, name: f.name || "image", url: URL.createObjectURL(f), status: "queued", error: null, layout: null }));
    el.picker.hidden = true;
    el.work.hidden = el.another.hidden = false;
    if (first === 0) showImage(0); else renderTabs();
    readNew(valid.map((_, k) => first + k));
  }

  // ---------- wiring ----------
  el.drop.addEventListener("click", () => el.file.click());
  el.drop.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); el.file.click(); }
  });
  el.file.addEventListener("change", () => { const chosen = [...el.file.files]; el.file.value = ""; if (chosen.length) addFiles(chosen); });
  el.drop.addEventListener("dragover", (e) => { e.preventDefault(); el.drop.classList.add("over"); });
  el.drop.addEventListener("dragleave", () => el.drop.classList.remove("over"));
  el.drop.addEventListener("drop", (e) => {
    e.preventDefault();
    el.drop.classList.remove("over");
    const dropped = e.dataTransfer ? [...e.dataTransfer.files] : [];
    if (dropped.length) addFiles(dropped);
  });
  el.addMore.addEventListener("click", () => el.file.click());
  el.another.addEventListener("click", () => { if (confirmDiscard()) reset(); });
  el.addRow.addEventListener("click", addRow);
  el.nextFlag.addEventListener("click", goToNextFlag);
  el.layout.addEventListener("change", (e) => {
    const choice = e.target.value;
    if (!files.length || choice === layoutChoice) return;
    const message = files.length > 1
      ? `Reading all ${files.length} images again will replace your edits. Continue?`
      : "Reading the image again will replace your edits. Continue?";
    if (!confirmDiscard(message)) { selectLayout(layoutChoice); return; }
    rereadAll(choice);
  });
  el.download.addEventListener("click", downloadCsv);
  el.undoBtn.addEventListener("click", undoDelete);
  // Nothing is saved anywhere, so warn before a reload or close would throw edits away.
  window.addEventListener("beforeunload", (e) => { if (dirty) { e.preventDefault(); e.returnValue = ""; } });

  // Tell the user which mode the server is in, so demo data is never mistaken for a real reading.
  fetch("/health").then((r) => r.json()).then((h) => {
    if (h.mode === "demo") {
      el.banner.textContent = "Demo mode: the table you see is sample data. Your images are not read or sent anywhere.";
    } else if (h.mode === "no-key") {
      el.banner.textContent = "No API key is set, so reading is switched off. Set ANTHROPIC_API_KEY, or start the server with DEMO_MODE=1 to try sample data.";
    } else return;
    el.banner.hidden = false;
  }).catch(() => {});
})();
