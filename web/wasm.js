import { performanceWrapper } from "./utils.js";

const WASM_URL = new URL(
  "./mediainfo.js/MediaInfoModule.wasm",
  import.meta.url,
);

const WORKER_URL = new URL("./mediainfo-worker.js", import.meta.url);

let CONCURRENCY = 1;
let TIMEOUT_MS = 10000;

let workers = [];

// prefetch to browser http cache, useful for start download early for cases of slow network
export function prefetchWasm() {
  fetch(WASM_URL).catch(() => {});
}

// event listener per task will cause garbage collection overhead and risk of leaks
// single event listener per worker lifetime, callback is changed per task
function addWorkerEventListeners(workerHandle) {
  workerHandle.worker.addEventListener("message", (e) =>
    workerHandle.workerOnMessage?.(e),
  );
  workerHandle.worker.addEventListener("error", (e) =>
    workerHandle.workerOnError?.(e),
  );
}

function createWorkerPool(concurrency = CONCURRENCY) {
  if (workers.length > 0) return;

  workers = Array.from({ length: concurrency }, () => ({
    worker: new Worker(WORKER_URL),
    workerOnMessage: null,
    workerOnError: null,
  }));

  workers.forEach(addWorkerEventListeners);
}

export function terminateAllWorkers() {
  workers.forEach((workerHandle) => {
    try {
      workerHandle.worker.terminate();
    } catch {}
  });

  workers = [];
}

function respawnWorker(workerHandle) {
  try {
    workerHandle.worker.terminate();
  } catch {}

  workerHandle.worker = new Worker(WORKER_URL);
  addWorkerEventListeners(workerHandle);
}

function getWasmResult(file, workerHandle, timeoutMs = TIMEOUT_MS) {
  return new Promise((resolve) => {
    const cleanup = () => {
      clearTimeout(timer);
      workerHandle.workerOnMessage = null;
      workerHandle.workerOnError = null;
    };

    const timer = setTimeout(() => {
      // wasm state untrusted after hang
      respawnWorker(workerHandle);
      cleanup();
      resolve({
        success: false,
        error: `Timeout after ${timeoutMs / 1000}sec`,
      });
    }, timeoutMs);

    const onMessage = (e) => {
      if (e.data.error) respawnWorker(workerHandle);
      cleanup();
      resolve(e.data);
    };

    const onError = (err) => {
      cleanup();
      // wasm state untrusted after crash
      respawnWorker(workerHandle);
      resolve({
        success: false,
        error: err?.message || "Worker error",
      });
    };

    workerHandle.workerOnMessage = onMessage;
    workerHandle.workerOnError = onError;

    workerHandle.worker.postMessage(file);
  });
}

export async function processWasmFiles(
  files,
  successResults,
  failedResults,
  concurrency = CONCURRENCY,
  timeoutMs = TIMEOUT_MS,
  progressCallbackFn,
) {
  if (!files || files.length === 0) return;

  createWorkerPool(concurrency);

  let index = 0;

  const workerFn = async (workerHandle) => {
    while (index < files.length) {
      // assign current values synchronously before await, other workers will increment index concurrently  while this worker await
      const currIdx = index++;
      const file = files[currIdx];

      let result = await performanceWrapper(
        () => getWasmResult(file, workerHandle, timeoutMs),
        "parseMs",
      );

      result.file = file;

      if (result.success) successResults.push(result);
      else failedResults.push(result);

      progressCallbackFn?.({
        result,
        completed: successResults.length + failedResults.length,
      });
    }
  };

  try {
    await Promise.all(workers.map(workerFn));
  } finally {
    terminateAllWorkers();
  }
}
