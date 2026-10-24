import { formatDuration, formatSize, isVideo, getFolderName } from "./utils.js";
import { getFiles } from "./filesystem.js";
import { processNativeFiles } from "./native.js";
import { processWasmFiles, prefetchWasm } from "./wasm.js";

const NATIVE_EXT_RE = /\.(mp4|webm|mov|m4v)$/i;

const state = {
  folderMap: new Map(),
  total: { duration: 0, count: 0, size: 0 },
  isScanning: false,
};

const els = {
  landing: document.getElementById("landing"),
  dashboard: document.getElementById("dashboard"),
  dropZone: document.getElementById("drop-zone"),
  input: document.getElementById("folder-input"),
  tableBody: document.getElementById("table-body"),
  status: document.getElementById("status"),
  totalDur: document.getElementById("total-duration"),
  totalCount: document.getElementById("total-count"),
  totalSize: document.getElementById("total-size"),
  resetBtn: document.getElementById("reset-btn"),
};

["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
  els.dropZone.addEventListener(
    eventName,
    (e) => {
      e.preventDefault();
      e.stopPropagation();
    },
    false,
  );
});

els.dropZone.addEventListener("dragover", () =>
  els.dropZone.classList.add("dragover"),
);
els.dropZone.addEventListener("dragleave", () =>
  els.dropZone.classList.remove("dragover"),
);

els.dropZone.addEventListener("drop", async (e) => {
  els.dropZone.classList.remove("dragover");

  const items = e.dataTransfer.items;
  if (!items || items.length === 0) return;

  const files = await getFiles(items);

  if (files === null) {
    alert(
      "Drag and drop for folders is not supported in your browser. Please use the browse folder button instead.",
    );
    els.landing.classList.remove("hidden");
    els.dashboard.classList.add("hidden");
    return;
  }

  if (files.length > 0) {
    els.landing.classList.add("hidden");
    els.dashboard.classList.remove("hidden");
    els.status.innerText = "> Initializing scan...";
    handleFiles(files);
  }
});

els.input.addEventListener("change", (e) => {
  if (e.target.files.length > 0) {
    els.landing.classList.add("hidden");
    els.dashboard.classList.remove("hidden");
    els.status.innerText = "> Processing file structure...";
    handleFiles(Array.from(e.target.files));
  }
});

els.resetBtn.addEventListener("click", () => location.reload());

function getConcurrency() {
  const userInputNative = window.prompt(
    "Enter browser native concurrency:",
    "1",
  );
  const userInputWasm = window.prompt("Enter mediainfo wasm concurrency:", "1");
  return {
    nativeConcurrency: parseInt(userInputNative, 10) || 1,
    wasmConcurrency: parseInt(userInputWasm, 10) || 1,
  };
}

function handleFiles(rawFiles) {
  const videoFiles = rawFiles.filter(isVideo);

  if (videoFiles.length > 0) {
    const { nativeConcurrency, wasmConcurrency } = getConcurrency();

    const nativeTimeoutMs = 10000;
    const wasmTimeoutMs = 10000;

    initializeFolders(videoFiles);

    processFiles(
      videoFiles,
      nativeConcurrency,
      nativeTimeoutMs,
      wasmConcurrency,
      wasmTimeoutMs,
    );
  }
}

function initializeFolders(files) {
  state.folderMap.clear();
  els.tableBody.innerHTML = "";

  files.forEach((file) => {
    const folderName = getFolderName(file);

    if (!state.folderMap.has(folderName)) {
      const rowId = `row-${Math.random().toString(36).substring(2, 11)}`;
      state.folderMap.set(folderName, {
        count: 0,
        duration: 0,
        size: 0,
        rowId: rowId,
      });
      createTableRow(folderName, rowId);
    }

    const folderData = state.folderMap.get(folderName);
    folderData.size += file.size;
    folderData.count++;
  });

  state.folderMap.forEach((data, name) => updateFolderRow(name));
  updateTotalStats();
}

function saveDurationToState(file, duration) {
  if (duration <= 0) return;

  const folderName = getFolderName(file);
  const folder = state.folderMap.get(folderName);

  if (folder) {
    folder.duration += duration;
    state.total.duration += duration;
    updateFolderRow(folderName);
    updateTotalStats();
  }
}

function createTableRow(folderName, rowId) {
  const row = document.createElement("tr");
  row.id = rowId;
  row.innerHTML = `<td class="folder-path">${folderName}</td><td class="col-count">0</td><td class="col-dur">00:00:00</td><td class="col-size">0 MB</td>`;
  els.tableBody.appendChild(row);
}

function updateFolderRow(folderName) {
  const data = state.folderMap.get(folderName);
  const row = document.getElementById(data.rowId);
  if (!row) return;
  row.querySelector(".col-count").innerText = data.count;
  row.querySelector(".col-dur").innerText = formatDuration(data.duration);
  row.querySelector(".col-size").innerText = formatSize(data.size);
}

function updateTotalStats() {
  let totalFiles = 0;
  let totalSize = 0;
  state.folderMap.forEach((d) => {
    totalFiles += d.count;
    totalSize += d.size;
  });
  els.totalCount.innerText = totalFiles;
  els.totalSize.innerText = formatSize(totalSize);
  els.totalDur.innerText = formatDuration(state.total.duration);
}

async function processFiles(
  files,
  nativeConcurrency,
  nativeTimeoutMs,
  wasmConcurrency,
  wasmTimeoutMs,
) {
  state.isScanning = true;

  const successResults = [];
  const failedResults = [];

  const nativeQueue = [];
  let wasmQueue = [];

  files.forEach((file) => {
    if (NATIVE_EXT_RE.test(file.name)) nativeQueue.push(file);
    else wasmQueue.push(file);
  });

  if (wasmQueue.length > 0) {
    prefetchWasm();
  }

  const progressCallbackFn = ({ result, completed }) => {
    els.status.innerText = `> Processed ${completed} of ${files.length}... (${result.file.name})`;
    if (result.success) saveDurationToState(result.file, result.duration);
  };

  const nativeFailed = [];

  processNativeFiles(
    nativeQueue,
    successResults,
    failedResults,
    nativeConcurrency,
    nativeTimeoutMs,
    progressCallbackFn,
  );

  wasmQueue.push(...nativeFailed);

  processWasmFiles(
    wasmQueue,
    successResults,
    failedResults,
    wasmConcurrency,
    wasmTimeoutMs,
    progressCallbackFn,
  );

  els.status.innerText = "> Scan Complete.";
  state.isScanning = false;
}
