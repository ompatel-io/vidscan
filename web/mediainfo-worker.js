importScripts("./mediainfo.js/index.min.js");

let mediainfoInstance = null;

self.onmessage = async (e) => {
  const file = e.data;

  if (!file || file.size === 0) {
    self.postMessage({
      success: false,
      message: !file ? "File not provided" : "File size 0",
    });
    return;
  }

  try {
    if (!mediainfoInstance) {
      mediainfoInstance = await MediaInfo.mediaInfoFactory({
        format: "object",
        locateFile: () => "./mediainfo.js/MediaInfoModule.wasm",
      });
    }

    const readChunk = async (chunkSize, offset) => {
      const buffer = await file.slice(offset, offset + chunkSize).arrayBuffer();
      return new Uint8Array(buffer);
    };

    const result = await mediainfoInstance.analyzeData(file.size, readChunk);
    const tracks = result?.media?.track;

    if (!Array.isArray(tracks) || tracks.length === 0) {
      self.postMessage({
        success: false,
        message: "File unrecognized or not supported by mediainfo",
      });
      return;
    }

    const generalTrack = tracks.find((t) => t["@type"] === "General");
    const videoTrack = tracks.find((t) => t["@type"] === "Video");
    const audioTrack = tracks.find((t) => t["@type"] === "Audio");

    const durationFieldExists =
      (generalTrack && "Duration" in generalTrack) ||
      (videoTrack && "Duration" in videoTrack) ||
      (audioTrack && "Duration" in audioTrack);

    if (!durationFieldExists) {
      self.postMessage({
        success: false,
        message: "Duration field not found in any mediainfo track",
      });
      return;
    }

    const mediainfoDurationSec =
      generalTrack?.Duration ?? videoTrack?.Duration ?? audioTrack?.Duration;

    const durationSec = parseFloat(mediainfoDurationSec);

    if (!Number.isFinite(durationSec) || durationSec <= 0) {
      self.postMessage({
        success: false,
        message: `Mediainfo returned duration '${mediainfoDurationSec}'`,
      });
      return;
    }

    self.postMessage({
      success: true,
      duration: durationSec,
    });
  } catch (err) {
    self.postMessage({
      success: false,
      error:
        err.message ||
        String(err) ||
        "An unknown error occurred in mediainfo worker",
    });
  }
};
