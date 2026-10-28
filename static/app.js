// Upload, review, and edit page (steps 3-5). Plain JavaScript, no build step.
// Privacy: the image is previewed from a local object URL and sent only to /api/extract.
// Edits and the CSV are built in this browser tab and never sent anywhere; closing the tab discards them.
// Text that comes back from a document is only ever inserted as plain text or as input values, never as markup.
(() => {
  const MAX_MB = 5; // matches the server default; the server's answer is the final word
  const $ = (id) => document.getElementById(id);
  const el = {
    drop: $("drop"), file: $("file"), status: $("status"), banner: $("mode-banner"),
    picker: $("picker"), work: $("work"), preview: $("preview"), summary: $("summary"),
    result: $("result"), rawWrap: $("raw-wrap"), raw: $("raw"), another: $("another"),
    tools: $("tools"), addRow: $("add-row"), download: $("download"),
    nextFlag: $("next-flag"), flagCount: $("flag-count"),
    undo: $("undo"), undoText: $("undo-text"), undoBtn: $("undo-btn"),
  };
  let objectUrl = null;
  let controller = null;
  let state = null;     // { columns: [string], rows: [[{ v, low }]] } - the table being edited
  let layout = "";
  let dirty = false;    // edits not yet downloaded
  let undoInfo = null;  // the last deleted row, so it can be restored
  let flagCursor = null; // the flagged cell the user was last taken to

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
  function toCsv(columns, rows) {
    const lines = [columns, ...rows.map((r) => r.map((c) => c.v))];
    return lines.map((l) => l.map(csvField).join(",")).join("\r\n") + "\r\n";
  }
  function downloadCsv() {
    // The BOM makes Excel read accents and non-English text correctly.
    const blob = new Blob(["\ufeff" + toCsv(state.columns, state.rows)], { type: "text/csv;charset=utf-8" });
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
  function updateSummary() {
    el.summary.textContent = `Layout: ${layout} · ${state.rows.length} row(s) · ${state.columns.length} column(s)`;
  }
  function confirmDiscard() {
    return !dirty || window.confirm("You have edits that have not been downloaded. Discard them?");
  }

  function reset() {
    if (controller) controller.abort();
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = controller = state = null;
    dirty = false;
    clearUndo();
    el.preview.removeAttribute("src");
    el.result.replaceChildren();
    el.summary.textContent = "";
    el.raw.textContent = "";
    el.rawWrap.hidden = el.tools.hidden = el.work.hidden = el.another.hidden = true;
    el.picker.hidden = false;
    setStatus("");
  }

  // ---------- uncertain-cell flags ----------
  // A cell is flagged when the reader was unsure (messy handwriting, blur, a guess). It is cleared only when
  // the user edits it or presses the check mark, never just because they looked at it.
  function countFlags() {
    return state ? state.rows.reduce((n, row) => n + row.filter((c) => c.low).length, 0) : 0;
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

  // ---------- editable table ----------
  function autosize(ta) {
    ta.style.height = "auto";
    if (ta.scrollHeight) ta.style.height = ta.scrollHeight + "px";
  }

  function buildRow(row, r) {
    const tr = document.createElement("tr");
    row.forEach((cell, c) => {
      const td = tr.insertCell();
      const ta = document.createElement("textarea");
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
        if (next) next.cells[c].querySelector("textarea").focus();
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
    el.result.replaceChildren();
    const table = document.createElement("table");
    const head = table.createTHead().insertRow();
    state.columns.forEach((name, c) => {
      const input = document.createElement("input");
      input.type = "text";
      input.value = name;
      input.setAttribute("aria-label", `Column ${c + 1} name`);
      input.addEventListener("input", () => { state.columns[c] = input.value; dirty = true; });
      const th = document.createElement("th");
      th.scope = "col";
      th.appendChild(input);
      head.appendChild(th);
    });
    head.appendChild(document.createElement("th"));
    const body = table.createTBody();
    state.rows.forEach((row, r) => body.appendChild(buildRow(row, r)));
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
    if (window.requestAnimationFrame) {
      requestAnimationFrame(() => el.result.querySelectorAll("textarea").forEach(autosize));
    }
  }

  function addRow() {
    clearUndo();
    state.rows.push(state.columns.map(() => ({ v: "", low: false })));
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

  // ---------- reading an image ----------
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
    if (!confirmDiscard()) return;
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
      layout = data.layout;
      state = { columns: data.columns.slice(), rows: data.rows.map((r) => r.map((c) => ({ v: c.v, low: !!c.low }))) };
      renderTable();
      el.tools.hidden = false;
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

  // ---------- wiring ----------
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
  el.another.addEventListener("click", () => { if (confirmDiscard()) reset(); });
  el.addRow.addEventListener("click", addRow);
  el.nextFlag.addEventListener("click", goToNextFlag);
  el.download.addEventListener("click", downloadCsv);
  el.undoBtn.addEventListener("click", undoDelete);
  // Nothing is saved anywhere, so warn before a reload or close would throw edits away.
  window.addEventListener("beforeunload", (e) => { if (dirty) { e.preventDefault(); e.returnValue = ""; } });

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
