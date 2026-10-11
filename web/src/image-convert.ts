export type OutputFormat = "image/jpeg" | "image/png" | "image/webp" | "image/bmp";

export interface ConvertOptions {
  format: OutputFormat;
  quality: number; // 1..100
}

export interface ConvertResult {
  fileName: string;
  originalSize: number;
  outputSize: number;
  blob: Blob;
}

const EXT: Record<OutputFormat, string> = {
  "image/jpeg": ".jpg",
  "image/png": ".png",
  "image/webp": ".webp",
  "image/bmp": ".bmp",
};

export async function convertImage(
  file: File,
  options: ConvertOptions,
): Promise<ConvertResult> {
  const source = await loadSource(file);

  const canvas = document.createElement("canvas");
  canvas.width = source.width;
  canvas.height = source.height;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Could not get 2D context");

  // JPEG has no alpha channel — flatten onto white.
  if (options.format === "image/jpeg") {
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  ctx.drawImage(source as CanvasImageSource, 0, 0);
  if ("close" in source && typeof source.close === "function") source.close();

  let blob: Blob | null;
  if (options.format === "image/bmp") {
    blob = await canvasToBmp(canvas);
  } else {
    const q = options.format === "image/png" ? undefined : options.quality / 100;
    blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, options.format, q),
    );
  }

  if (!blob) throw new Error("Encoding failed");

  const base = file.name.replace(/\.[^.]+$/, "") || "image";
  return {
    fileName: base + EXT[options.format],
    originalSize: file.size,
    outputSize: blob.size,
    blob,
  };
}

async function loadSource(
  file: File,
): Promise<ImageBitmap | HTMLImageElement> {
  try {
    return await createImageBitmap(file);
  } catch {
    // Fallback for browsers that can't decode the format via createImageBitmap
    return await new Promise<HTMLImageElement>((resolve, reject) => {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error("Unsupported image"));
      };
      img.src = url;
    });
  }
}

/**
 * Minimal 24-bit uncompressed BMP encoder.
 * The browser's canvas.toBlob() doesn't support BMP, so we roll our own.
 */
async function canvasToBmp(canvas: HTMLCanvasElement): Promise<Blob> {
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Could not get 2D context");
  const { width, height } = canvas;
  const { data } = ctx.getImageData(0, 0, width, height);

  const rowSize = Math.ceil((width * 3) / 4) * 4;
  const pixelBytes = rowSize * height;
  const fileHeaderSize = 14;
  const dibHeaderSize = 40;
  const fileSize = fileHeaderSize + dibHeaderSize + pixelBytes;

  const buf = new ArrayBuffer(fileSize);
  const view = new DataView(buf);
  const bytes = new Uint8Array(buf);

  // BITMAPFILEHEADER
  bytes[0] = 0x42; // 'B'
  bytes[1] = 0x4d; // 'M'
  view.setUint32(2, fileSize, true);
  view.setUint32(10, fileHeaderSize + dibHeaderSize, true);

  // BITMAPINFOHEADER
  view.setUint32(14, dibHeaderSize, true);
  view.setInt32(18, width, true);
  view.setInt32(22, -height, true); // negative = top-down (no flip needed)
  view.setUint16(26, 1, true);      // planes
  view.setUint16(28, 24, true);     // bits per pixel
  view.setUint32(34, pixelBytes, true);
  view.setInt32(38, 2835, true);    // ~72 DPI
  view.setInt32(42, 2835, true);

  // Pixel data (BGR order, rows already aligned via rowSize)
  let p = fileHeaderSize + dibHeaderSize;
  for (let y = 0; y < height; y++) {
    let row = p + y * rowSize;
    for (let x = 0; x < width; x++) {
      const i = (y * width + x) * 4;
      bytes[row++] = data[i + 2]; // B
      bytes[row++] = data[i + 1]; // G
      bytes[row++] = data[i];     // R
    }
    // Padding bytes remain 0.
  }

  return new Blob([buf], { type: "image/bmp" });
}
