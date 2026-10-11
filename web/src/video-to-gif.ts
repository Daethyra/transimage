import { fetchFile } from "@ffmpeg/util";
import { loadFFmpeg } from "./ffmpeg";

export interface GifOptions {
  fps: number;
  width?: number;                                     // max width; height auto (keeps aspect)
  colors: number;                                     // 2..256
  dither: boolean;
  loop: number;                                       // 0 = infinite
  startTime?: number;                                 // seconds
  endTime?: number;                                   // seconds
  crop?: [number, number, number, number];            // left, top, right, bottom
}

export interface GifResult {
  blob: Blob;
  fileName: string;
}

export async function videoToGif(
  file: File,
  options: GifOptions,
  onProgress: (ratio: number) => void,
  onStatus: (msg: string) => void,
): Promise<GifResult> {
  const ffmpeg = await loadFFmpeg(onStatus);

  const onFfmpegProgress = ({ progress }: { progress: number }) => {
    if (Number.isFinite(progress)) onProgress(Math.max(0, Math.min(1, progress)));
  };
  ffmpeg.on("progress", onFfmpegProgress);

  const inputName = `input${getExt(file.name)}`;
  const outputName = "output.gif";

  try {
    onStatus("Loading video into memory…");
    await ffmpeg.writeFile(inputName, await fetchFile(file));

    const filterChain = buildFilterChain(options);
    const dither = options.dither ? "floyd_steinberg" : "none";
    const filterComplex =
      `[0:v]${filterChain},split[a][b];` +
      `[a]palettegen=max_colors=${options.colors}:stats_mode=diff[p];` +
      `[b][p]paletteuse=dither=${dither}`;

    const args: string[] = [];

    // Fast seek: -ss before -i is much quicker on long videos.
    if (options.startTime !== undefined && options.startTime > 0) {
      args.push("-ss", String(options.startTime));
    }
    args.push("-i", inputName);

    // Duration cap (end - start, or end from 0).
    const start = options.startTime ?? 0;
    if (options.endTime !== undefined && options.endTime > start) {
      args.push("-t", String(options.endTime - start));
    }

    args.push(
      "-filter_complex", filterComplex,
      "-loop", String(options.loop),
      "-y",
      outputName,
    );

    onStatus("Encoding GIF — this may take a while for long videos…");
    onProgress(0);
    await ffmpeg.exec(args);

    onStatus("Reading result…");
    const data = (await ffmpeg.readFile(outputName)) as Uint8Array;

    // Copy into a fresh buffer so the Blob owns its memory.
    const copy = new Uint8Array(data.byteLength);
    copy.set(data);
    const blob = new Blob([copy.buffer], { type: "image/gif" });

    // Clean up the virtual filesystem so repeat runs don't leak memory.
    await ffmpeg.deleteFile(inputName).catch(() => {});
    await ffmpeg.deleteFile(outputName).catch(() => {});

    const base = file.name.replace(/\.[^.]+$/, "") || "output";
    return { blob, fileName: `${base}.gif` };
  } finally {
    ffmpeg.off("progress", onFfmpegProgress);
  }
}

function buildFilterChain(o: GifOptions): string {
  const filters: string[] = [];

  if (o.crop) {
    const [l, t, r, b] = o.crop;
    if (l || t || r || b) {
      // iw/ih are input width/height; keep at least 2 px in each dimension.
      filters.push(`crop=iw-${l + r}:ih-${t + b}:${l}:${t}`);
    }
  }

  if (o.width && o.width > 0) {
    // -2 forces the auto-computed height to be divisible by 2.
    filters.push(`scale=${o.width}:-2:flags=lanczos`);
  }

  filters.push(`fps=${o.fps}`);
  return filters.join(",");
}

function getExt(name: string): string {
  const m = name.match(/\.[^.]+$/);
  return m ? m[0].toLowerCase() : ".mp4";
}
