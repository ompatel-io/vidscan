export async function getFiles(items) {
  let files = [];

  if (!items[0].getAsFileSystemHandle) {
    return null;
  }

  for (const item of items) {
    try {
      const handle = await item.getAsFileSystemHandle();
      if (handle) {
        if (handle.kind === "directory") {
          const dirFiles = await walkDirHandle(handle);
          files.push(...dirFiles);
        } else {
          const file = await handle.getFile();
          file.fullPath = handle.name;
          files.push(file);
        }
      }
    } catch (err) {
      console.warn("Scan error:", err);
    }
  }
  return files;
}

async function walkDirHandle(dirHandle, path = "") {
  const files = [];
  const currentPath = path ? `${path}/${dirHandle.name}` : dirHandle.name;

  try {
    for await (const entry of dirHandle.values()) {
      if (entry.kind === "file") {
        const file = await entry.getFile();
        file.fullPath = `${currentPath}/${entry.name}`;
        files.push(file);
      } else if (entry.kind === "directory") {
        const subFiles = await walkDirHandle(entry, currentPath);
        files.push(...subFiles);
      }
    }
  } catch (err) {
    console.warn(`Error reading folder: ${dirHandle.name}`, err);
  }
  return files;
}
