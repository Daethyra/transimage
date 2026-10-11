/**
 * Lazy loader for ffmpeg.wasm. The first call downloads ~25 MB from a CDN,
 * the browser caches it, and every subsequent call returns the same instance.
 * All processing happens locally — nothing is ever uploaded.
 */
import { FFmpeg } from "@ffmpeg/ffmpeg";
import { toBlobURL } from "@ffmpeg/util";

const CORE_VERSION = "0.12.6";
const BASE_URL = `https://cdn.jsdelivr.net/npm/@ffmpeg/core@${CORE_VERSION}/dist/esm`;

let instance: Promise<FFmpeg> | null = null;

export function loadFFmpeg(onStatus: (msg: string) => void): Promise<FFmpeg> {
  if (!instance) {
    instance = (async () => {
      onStatus("Loading ffmpeg (~25 MB, cached after the first run)…");
      const ffmpeg = new FFmpeg();
      await ffmpeg.load({
        coreURL: await toBlobURL(`${BASE_URL}/ffmpeg-core.js`, "text/javascript"),
        wasmURL: await toBlobURL(`${BASE_URL}/ffmpeg-core.wasm`, "application/wasm"),
        classWorkerURL: `${location.origin}/ffmpeg/lib/worker.js`,
      });
      onStatus("ffmpeg ready.");
      return ffmpeg;
    })().catch((err) => {
      instance = null;
      throw err;
    });
  }
  return instance;
}
