export function formatDuration(sec) {
  if (!sec) return "00:00:00";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export function formatSize(bytes) {
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB";
}

export function isVideo(file) {
  return file.name.match(/\.(mp4|webm|mov|mkv|avi|flv|wmv|m4v)$/i);
}

export function getFolderName(file) {
  let fullPath = file.webkitRelativePath || file.fullPath || file.name;
  if (fullPath.startsWith("/")) fullPath = fullPath.substring(1);

  const pathParts = fullPath.split("/");
  if (pathParts.length > 1) {
    pathParts.pop();
  } else {
    return "Main Directory";
  }
  return pathParts.join("/");
}
