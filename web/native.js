let CONCURRENCY = 1;
let TIMEOUT_MS = 10000;

export function getNativeResult(file, timeoutMs = TIMEOUT_MS) {
  if (!file || file.size === 0) {
    return Promise.resolve({
      success: false,
      error: !file ? "File not provided" : "File size 0",
    });
  }

  return new Promise((resolve) => {
    const video = document.createElement("video");
    video.preload = "metadata";

    const objectUrl = URL.createObjectURL(file);

    let settled = false;

    const cleanup = () => {
      // clear handlers first before load to prevent metadata/error events
      video.onloadedmetadata = null;
      video.onerror = null;
      // remove src before load, so no source to fetch on
      video.removeAttribute("src");
      // media element load algorith without src: abort active work and reset
      video.load();
      // remove reference from browser memory
      URL.revokeObjectURL(objectUrl);
    };

    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      cleanup();
      resolve(result);
    };

    const timer = setTimeout(() => {
      finish({
        success: false,
        error: `Timeout after ${timeoutMs / 1000}sec`,
      });
    }, timeoutMs);

    video.onloadedmetadata = () => {
      const duration = video.duration;

      if (!Number.isFinite(duration) || duration <= 0) {
        finish({
          success: false,
          error: `Invalid duration (${duration})`,
        });
        return;
      }

      finish({
        success: true,
        duration,
      });
    };

    video.onerror = () => {
      finish({
        success: false,
        error: `Failed for native: ${file.name}`,
      });
    };

    video.src = objectUrl;
  });
}

export async function processNativeFiles(
  files,
  successResults,
  failedResults,
  concurrency = CONCURRENCY,
  timeoutMs = TIMEOUT_MS,
  progressCallbackFn,
) {
  if (!files || files.length === 0) return;

  let index = 0;

  const worker = async () => {
    while (index < files.length) {
      const currIdx = index++;
      const file = files[currIdx];

      let result = await getNativeResult(file, timeoutMs);

      result.file = file;

      if (result.success) successResults.push(result);
      else failedResults.push(result);

      progressCallbackFn?.({
        result,
        completed: successResults.length + failedResults.length,
      });
    }
  };

  const workerPromises = Array.from({ length: concurrency }, worker);
  await Promise.all(workerPromises);
}
