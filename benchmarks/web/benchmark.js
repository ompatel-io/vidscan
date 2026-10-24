import { processWasmFiles } from "../../web/src/wasm.js";
import { processNativeFiles } from "../../web/src/native.js";

const folderInput = document.getElementById("folder-input");
const extInput = document.getElementById("ext-input");
const concurrencyInput = document.getElementById("concurrency-input");
const timeoutInput = document.getElementById("timeout-input");
const runBtn = document.getElementById("run-btn");
const fileCountEl = document.getElementById("file-count");
const statusEl = document.getElementById("status");
const resultsBody = document.getElementById("results-body");
const exportCsvBtn = document.getElementById("export-csv-btn");
const methodRadios = document.querySelectorAll('input[name="method"]');

let allFolderFiles = [];
let selectedFiles = [];
let runRows = [];

const methodExtensions = {
  WASM: ".mkv",
  Native: ".mp4",
};

function getSelectedMethod() {
  const checked = document.querySelector('input[name="method"]:checked');
  return checked ? checked.value : "WASM";
}

function parseExtensions(rawStr) {
  return rawStr
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean)
    .map((ext) => (ext.startsWith(".") ? ext : `.${ext}`));
}

function updateFilteredFiles() {
  const method = getSelectedMethod();
  const exts = parseExtensions(extInput.value);

  if (allFolderFiles.length === 0) {
    selectedFiles = [];
    fileCountEl.textContent = "No folder selected.";
    runBtn.disabled = true;
    return;
  }

  selectedFiles = allFolderFiles.filter((f) => {
    const lowerName = f.name.toLowerCase();
    return exts.some((ext) => lowerName.endsWith(ext));
  });

  fileCountEl.textContent = `${selectedFiles.length} matching files [${method}] (of ${allFolderFiles.length} total in folder)`;
  runBtn.disabled = selectedFiles.length === 0;
}

folderInput.addEventListener("change", (e) => {
  allFolderFiles = Array.from(e.target.files || []);
  statusEl.textContent = "";
  updateFilteredFiles();
});

extInput.addEventListener("input", () => {
  const method = getSelectedMethod();
  methodExtensions[method] = extInput.value;
  if (statusEl.textContent.startsWith("Done")) statusEl.textContent = "";
  updateFilteredFiles();
});

methodRadios.forEach((radio) => {
  radio.addEventListener("change", () => {
    const method = getSelectedMethod();
    extInput.value = methodExtensions[method] || "";
    statusEl.textContent = "";
    updateFilteredFiles();
  });
});

concurrencyInput.addEventListener("input", () => {
  if (statusEl.textContent.startsWith("Done")) statusEl.textContent = "";
});

timeoutInput.addEventListener("input", () => {
  if (statusEl.textContent.startsWith("Done")) statusEl.textContent = "";
});

function setControlsDisabled(disabled) {
  folderInput.disabled = disabled;
  extInput.disabled = disabled;
  concurrencyInput.disabled = disabled;
  timeoutInput.disabled = disabled;
  methodRadios.forEach((r) => (r.disabled = disabled));
  runBtn.disabled = disabled || selectedFiles.length === 0;
}

function getTimestamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

async function run() {
  const method = getSelectedMethod();
  const concurrency = parseInt(concurrencyInput.value, 10);
  const timeoutMs = Math.max(100, parseInt(timeoutInput.value, 10) || 10000);

  if (!Number.isInteger(concurrency) || concurrency < 1) {
    alert("Enter a valid concurrency (whole number, 1 or higher)");
    return;
  }

  if (selectedFiles.length === 0) return;

  setControlsDisabled(true);

  const totalFiles = selectedFiles.length;
  const successResults = [];
  const failedResults = [];

  statusEl.textContent = `0 / ${totalFiles}`;

  const processFn = method === "WASM" ? processWasmFiles : processNativeFiles;

  const progressCallbackFn = ({ completed }) => {
    statusEl.textContent = `${completed} / ${totalFiles}`;
  };

  const start = performance.now();

  try {
    await processFn(
      selectedFiles,
      successResults,
      failedResults,
      concurrency,
      timeoutMs,
      progressCallbackFn,
    );
  } finally {
    setControlsDisabled(false);
  }

  const totalMs = performance.now() - start;
  const filesPerSec = parseFloat((totalFiles / (totalMs / 1000)).toFixed(2));

  const avgParseMs = successResults.length
    ? Math.round(
        successResults.reduce((acc, r) => acc + (r.parseMs || 0), 0) /
          successResults.length,
      )
    : 0;

  const row = {
    timestamp: getTimestamp(),
    method,
    concurrency,
    files: totalFiles,
    totalMs: Math.round(totalMs),
    filesPerSec,
    avgParseMs,
    success: successResults.length,
    failed: failedResults.length,
  };

  runRows.push(row);
  exportCsvBtn.disabled = false;

  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${row.timestamp}</td>
    <td>${row.method}</td>
    <td>${row.concurrency}</td>
    <td>${row.files}</td>
    <td>${row.totalMs}</td>
    <td><strong>${row.filesPerSec.toFixed(2)}</strong></td>
    <td>${row.avgParseMs}</td>
    <td>${row.success}</td>
    <td>${row.failed}</td>
  `;
  resultsBody.appendChild(tr);

  statusEl.textContent = `Done: ${totalFiles} files`;
}

function exportCSV() {
  if (runRows.length === 0) return;

  const keys = Object.keys(runRows[0]);
  const lines = [keys.join(",")];

  for (const row of runRows) {
    lines.push(keys.map((k) => JSON.stringify(row[k] ?? "")).join(","));
  }

  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "web_benchmark.csv";
  a.click();
  URL.revokeObjectURL(url);
}

runBtn.addEventListener("click", run);
exportCsvBtn.addEventListener("click", exportCSV);

extInput.value = methodExtensions[getSelectedMethod()];
exportCsvBtn.disabled = true;
