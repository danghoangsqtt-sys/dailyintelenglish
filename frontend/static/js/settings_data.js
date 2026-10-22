/**
 * Phase 70 (ENH-052): Settings -> Data & sync. Export the library package (characters, libraries, channel plan) and import one
 * from another machine; the import merges and never deletes.
 */
(() => {
  const $ = (id) => document.getElementById(id);
  const LABELS = [["characters", "characters", "#1F7A4D"], ["character_assets", "character pictures", "#7E6BE0"],
    ["activity_library", "activities", "#E0A100"], ["scenes", "scenes", "#5B8DEF"], ["music_tracks", "music tracks", "#E07BB0"],
    ["channel_series", "channel series", "#3B4A44"]];
  const size = (bytes) => bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : `${Math.max(1, Math.round(bytes / 1e6))} MB`;

  function tile(value, label, colour) {
    const node = document.createElement("div");
    node.className = "kpi";
    node.style.setProperty("--kpi", colour);
    const number = document.createElement("b");
    number.textContent = String(value);
    const text = document.createElement("span");
    text.textContent = label;
    node.append(number, text);
    return node;
  }

  function link(name) {
    const item = document.createElement("li");
    const anchor = document.createElement("a");
    anchor.href = `/api/library-package/download/${encodeURIComponent(name)}`;
    anchor.textContent = name;
    anchor.setAttribute("download", name);
    item.append(anchor);
    return item;
  }

  async function load() {
    try {
      const data = await Api.getLibraryPackage();
      $("package-counts").replaceChildren(...LABELS.map(([key, label, colour]) => tile(data.counts[key] ?? 0, label, colour)),
        tile(`${data.files}`, `files · ${size(data.bytes)}`, "#9AA5A0"));
      $("package-exports").replaceChildren(...data.exports.map(link));
    } catch (error) {
      $("package-export-status").textContent = error.message || "The library could not be read.";
    }
  }

  $("package-export").addEventListener("click", async () => {
    const button = $("package-export");
    button.disabled = true;
    $("package-export-status").textContent = "Writing the package… (a minute or two for a large library)";
    try {
      const result = await Api.exportLibraryPackage();
      $("package-export-status").textContent = `Saved ${result.name} (${size(result.bytes)}) in ${result.folder}`;
      await load();
    } catch (error) {
      $("package-export-status").textContent = error.message || "The package could not be written.";
    } finally {
      button.disabled = false;
    }
  });

  $("package-file").addEventListener("change", () => { $("package-import").disabled = !$("package-file").files.length; });
  $("package-import").addEventListener("click", async () => {
    const file = $("package-file").files[0];
    if (!file) return;
    if (!(await ConfirmDialog.ask(`Import "${file.name}"? New items are added and older ones updated; nothing is deleted.`, { confirmLabel: "Import" }))) return;
    $("package-import").disabled = true;
    $("package-import-status").textContent = "Importing…";
    try {
      const result = await Api.importLibraryPackage(file);
      const rows = Object.values(result.tables).reduce((sum, part) => ({ added: sum.added + part.added, updated: sum.updated + part.updated }), { added: 0, updated: 0 });
      $("package-import-status").textContent = `Imported: ${rows.added} added, ${rows.updated} updated; ${result.files.added + result.files.updated} files copied. Backup: ${result.backup}`;
      await load();
    } catch (error) {
      $("package-import-status").textContent = error.message || "The package could not be imported.";
    } finally {
      $("package-import").disabled = false;
    }
  });

  load();
})();
