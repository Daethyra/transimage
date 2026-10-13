import "./style.css";
import { fetchFile } from "@ffmpeg/util";
import { loadFFmpeg } from "./ffmpeg";
import { videoToGif, type GifOptions } from "./video-to-gif";
import { convertImage, type OutputFormat } from "./image-convert";
import { $, clamp, escapeHtml, formatBytes, optionalFloat, optionalInt } from "./utils";

/* =================== Small helpers =================== */

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0.00s";
  return `${seconds.toFixed(2)}s`;
}

function showError(el: HTMLElement, msg: string): void {
  el.textContent = msg;
  el.classList.remove("hidden");
  window.setTimeout(() => el.classList.add("hidden"), 8000);
}

function wireDropzone(
  zone: HTMLElement,
  onFiles: (files: File[]) => void,
  accept: (f: File) => boolean,
): void {
  for (const ev of ["dragenter", "dragover"] as const) {
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.add("dragover");
    });
  }
  for (const ev of ["dragleave", "drop"] as const) {
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.remove("dragover");
    });
  }
  zone.addEventListener("drop", (e) => {
    const dt = (e as DragEvent).dataTransfer;
    if (!dt) return;
    const files = Array.from(dt.files).filter(accept);
    if (files.length) onFiles(files);
  });
}

/**
 * Best-effort "is this actually a video?" check. Prefers the MIME type, but
 * trusts a known extension when MIME is missing or generic (common on Linux).
 */
const VIDEO_EXTS = [".mp4", ".mov", ".webm", ".mkv", ".avi", ".flv", ".m4v", ".mpg", ".mpeg", ".3gp", ".ogv"];
function looksLikeVideo(file: File): boolean {
  if (file.type.startsWith("video/")) return true;
  const m = file.name.toLowerCase().match(/\.[^.]+$/);
  return !!m && VIDEO_EXTS.includes(m[0]);
}

/* =================== Tabs =================== */

const tabs = document.querySelectorAll<HTMLButtonElement>(".tabs button");
const panels: Record<string, HTMLElement> = {
  gif: $("#panel-gif"),
  convert: $("#panel-convert"),
};

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const target = tab.dataset.tab!;
    tabs.forEach((t) => {
      const active = t === tab;
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
    for (const [key, panel] of Object.entries(panels)) {
      panel.classList.toggle("hidden", key !== target);
    }
  });
});

/* =================== Video → GIF =================== */

const gifFileInput = $<HTMLInputElement>("#gif-file");
const gifDrop = $("#gif-drop");
const gifBrowse = $<HTMLButtonElement>("#gif-browse");
const gifFileInfo = $("#gif-file-info");
const gifConvert = $<HTMLButtonElement>("#gif-convert");
const gifError = $("#gif-error");
const gifProgress = $("#gif-progress");
const gifProgressFill = $<HTMLDivElement>("#gif-progress-fill");
const gifStatus = $("#gif-status");
const gifResult = $("#gif-result");
const gifPreview = $<HTMLImageElement>("#gif-preview");
const gifResultMeta = $("#gif-result-meta");
const gifDownload = $<HTMLAnchorElement>("#gif-download");
const gifReset = $<HTMLButtonElement>("#gif-reset");

// Preview + scrub
const gifPreviewWrap = $("#gif-preview-wrap");
const gifPreviewVideo = $<HTMLVideoElement>("#gif-preview-video");
const gifPreviewPoster = $<HTMLImageElement>("#gif-preview-poster");
const gifPreviewNote = $<HTMLParagraphElement>("#gif-preview-note");
const gifScrub = $("#gif-scrub");
const gifScrubRange = $<HTMLInputElement>("#gif-scrub-range");
const gifTimeCurrent = $("#gif-time-current");
const gifTimeTotal = $("#gif-time-total");
const gifSetStart = $<HTMLButtonElement>("#gif-set-start");
const gifSetEnd = $<HTMLButtonElement>("#gif-set-end");
const gifStartInput = $<HTMLInputElement>("#gif-start");
const gifEndInput = $<HTMLInputElement>("#gif-end");

const VIDEO_LOAD_TIMEOUT_MS = 6000;

let gifFile: File | null = null;
let gifPreviewUrl: string | null = null;
let gifPreviewFallbackUrl: string | null = null;
let gifPreviewInFallbackMode = false;
let gifPreviewLoadTimer: number | null = null;

function clearGifPreviewTimer(): void {
  if (gifPreviewLoadTimer !== null) {
    window.clearTimeout(gifPreviewLoadTimer);
    gifPreviewLoadTimer = null;
  }
}

function startGifPreviewTimer(): void {
  clearGifPreviewTimer();
  gifPreviewLoadTimer = window.setTimeout(() => {
    gifPreviewLoadTimer = null;
    void enterFallbackMode();
  }, VIDEO_LOAD_TIMEOUT_MS);
}

/**
 * The browser's <video> element is opaque - some codecs and container
 * formats silently fail to load. When that happens, use ffmpeg.wasm to
 * decode a single frame and show it as a poster image. This mirrors what
 * the conversion pipeline will actually do, so it's a reliable preview.
 */
async function enterFallbackMode(): Promise<void> {
  if (gifPreviewInFallbackMode || !gifFile) return;
  gifPreviewInFallbackMode = true;
  clearGifPreviewTimer();

  // Swap video for poster + note.
  gifPreviewVideo.classList.add("hidden");
  gifPreviewPoster.classList.remove("hidden");
  gifPreviewNote.classList.remove("hidden");
  gifPreviewNote.textContent = "Preparing preview…";
  gifScrub.classList.add("hidden");

  const file = gifFile; // capture for the async body

  try {
    const ffmpeg = await loadFFmpeg((msg) => {
      // Only overwrite the note while we're still in the loading phase.
      if (!gifPreviewPoster.src) gifPreviewNote.textContent = msg;
    });

    const extMatch = file.name.toLowerCase().match(/\.[^.]+$/);
    const ext = extMatch ? extMatch[0] : ".mp4";
    const inputName = "preview-input" + ext;
    const outputName = "preview-frame.png";

    await ffmpeg.writeFile(inputName, await fetchFile(file));

    // Try a slightly into the video; fall back to frame 0 if that yields nothing.
    const trySeek = async (seek: string) =>
      ffmpeg.exec([
        "-ss", seek,
        "-i", inputName,
        "-frames:v", "1",
        "-y",
        outputName,
      ]);

    try {
      await trySeek("0.1");
      // If the output is empty, ffmpeg would have errored; nothing more to do.
    } catch {
      await trySeek("0");
    }

    const data = (await ffmpeg.readFile(outputName)) as Uint8Array;
    if (!data || data.byteLength === 0) {
      throw new Error("Empty frame from ffmpeg");
    }
    const copy = new Uint8Array(data.byteLength);
    copy.set(data);
    const blob = new Blob([copy.buffer], { type: "image/png" });

    // Clean up the virtual FS.
    await ffmpeg.deleteFile(inputName).catch(() => {});
    await ffmpeg.deleteFile(outputName).catch(() => {});

    if (gifPreviewFallbackUrl) URL.revokeObjectURL(gifPreviewFallbackUrl);
    gifPreviewFallbackUrl = URL.createObjectURL(blob);
    gifPreviewPoster.src = gifPreviewFallbackUrl;

    gifPreviewNote.textContent =
      "Live preview isn’t available for this file - showing a frame extracted from the video. " +
      "Start/End times can still be typed manually below.";
  } catch (err) {
    console.error(err);
    gifPreviewPoster.classList.add("hidden");
    gifPreviewNote.textContent =
      "Could not generate a preview for this file. You can still create a GIF using the fields below.";
  }
}

function setGifFile(file: File | null): void {
  gifFile = file;
  gifConvert.disabled = !file;
  gifResult.classList.add("hidden");
  gifProgress.classList.add("hidden");
  gifError.classList.add("hidden");

  // Tear down any previous preview state.
  clearGifPreviewTimer();
  gifPreviewInFallbackMode = false;

  if (gifPreviewUrl) {
    URL.revokeObjectURL(gifPreviewUrl);
    gifPreviewUrl = null;
  }
  if (gifPreviewFallbackUrl) {
    URL.revokeObjectURL(gifPreviewFallbackUrl);
    gifPreviewFallbackUrl = null;
  }

  gifPreviewVideo.pause();
  gifPreviewVideo.removeAttribute("src");
  gifPreviewVideo.load();
  gifPreviewVideo.classList.remove("hidden");
  gifPreviewPoster.removeAttribute("src");
  gifPreviewPoster.classList.add("hidden");
  gifPreviewNote.textContent = "";
  gifPreviewNote.classList.add("hidden");
  gifPreviewWrap.classList.add("hidden");
  gifScrub.classList.add("hidden");
  gifScrubRange.value = "0";
  gifTimeCurrent.textContent = "0.00s";
  gifTimeTotal.textContent = "0.00s";

  if (file) {
    gifFileInfo.innerHTML =
      `<span class="name">${escapeHtml(file.name)}</span>` +
      `<span class="size">${formatBytes(file.size)}</span>`;
    gifFileInfo.classList.remove("hidden");

    gifPreviewUrl = URL.createObjectURL(file);
    gifPreviewVideo.src = gifPreviewUrl;
    gifPreviewVideo.load();
    gifPreviewWrap.classList.remove("hidden");

    // Arm the fallback timer. If loadedmetadata (or error) doesn't fire
    // within VIDEO_LOAD_TIMEOUT_MS, switch to the ffmpeg-based preview.
    startGifPreviewTimer();
  } else {
    gifFileInfo.classList.add("hidden");
  }
}

gifPreviewVideo.addEventListener("loadedmetadata", () => {
  if (!gifFile) return;
  clearGifPreviewTimer();

  const duration = gifPreviewVideo.duration;
  if (!Number.isFinite(duration) || duration <= 0) {
    // Metadata fired but the duration is unusable - treat as a failed preview.
    void enterFallbackMode();
    return;
  }

  gifScrubRange.max = String(duration);
  gifScrubRange.value = "0";
  gifTimeTotal.textContent = formatTime(duration);
  gifTimeCurrent.textContent = formatTime(0);
  gifScrub.classList.remove("hidden");

  gifFileInfo.innerHTML =
    `<span class="name">${escapeHtml(gifFile.name)}</span>` +
    `<span class="size">${formatBytes(gifFile.size)} · ${formatTime(duration)}</span>`;

  // Nudge the playhead so a frame is painted instead of a black box.
  try {
    gifPreviewVideo.currentTime = Math.min(0.05, duration / 2);
  } catch {
    /* Some browsers throw if the currentTime is out of range. */
  }
});

gifPreviewVideo.addEventListener("error", () => {
  if (!gifFile) return;
  void enterFallbackMode();
});

gifScrubRange.addEventListener("input", () => {
  const t = parseFloat(gifScrubRange.value);
  if (Number.isFinite(t)) gifPreviewVideo.currentTime = t;
});

gifPreviewVideo.addEventListener("timeupdate", () => {
  // Don't fight the user while they're dragging the slider.
  if (document.activeElement !== gifScrubRange) {
    gifScrubRange.value = String(gifPreviewVideo.currentTime);
  }
  gifTimeCurrent.textContent = formatTime(gifPreviewVideo.currentTime);
});

gifSetStart.addEventListener("click", () => {
  if (gifPreviewInFallbackMode) return;
  gifStartInput.value = gifPreviewVideo.currentTime.toFixed(2);
});

gifSetEnd.addEventListener("click", () => {
  if (gifPreviewInFallbackMode) return;
  gifEndInput.value = gifPreviewVideo.currentTime.toFixed(2);
});

gifBrowse.addEventListener("click", (e) => {
  e.stopPropagation();
  gifFileInput.click();
});
gifDrop.addEventListener("click", () => gifFileInput.click());

gifFileInput.addEventListener("change", () => {
  const f = gifFileInput.files?.[0];
  if (!f) return;
  if (!looksLikeVideo(f)) {
    showError(gifError, "That file doesn’t look like a video. Try an MP4, MOV, WebM, or MKV.");
    gifFileInput.value = "";
    return;
  }
  setGifFile(f);
});

wireDropzone(
  gifDrop,
  (files) => {
    if (!files[0]) return;
    setGifFile(files[0]);
  },
  looksLikeVideo,
);

gifConvert.addEventListener("click", async () => {
  if (!gifFile) return;

  const options: GifOptions = {
    fps: clamp(parseFloat($<HTMLInputElement>("#gif-fps").value), 1, 60, 15),
    width: optionalInt($<HTMLInputElement>("#gif-width").value, 16, 1920),
    colors: clamp(parseFloat($<HTMLInputElement>("#gif-colors").value), 2, 256, 256),
    dither: $<HTMLInputElement>("#gif-dither").checked,
    loop: parseInt($<HTMLSelectElement>("#gif-loop").value, 10) || 0,
    startTime: optionalFloat($<HTMLInputElement>("#gif-start").value, 0),
    endTime: optionalFloat($<HTMLInputElement>("#gif-end").value, 0),
  };

  const crop: [number, number, number, number] = [
    clamp(parseFloat($<HTMLInputElement>("#gif-crop-l").value), 0, 10000, 0),
    clamp(parseFloat($<HTMLInputElement>("#gif-crop-t").value), 0, 10000, 0),
    clamp(parseFloat($<HTMLInputElement>("#gif-crop-r").value), 0, 10000, 0),
    clamp(parseFloat($<HTMLInputElement>("#gif-crop-b").value), 0, 10000, 0),
  ];
  if (crop.some((v) => v > 0)) options.crop = crop;

  if (
    options.startTime !== undefined &&
    options.endTime !== undefined &&
    options.endTime <= options.startTime
  ) {
    showError(gifError, "End time must be greater than start time.");
    return;
  }

  gifConvert.disabled = true;
  gifResult.classList.add("hidden");
  gifError.classList.add("hidden");
  gifProgress.classList.remove("hidden");
  gifProgressFill.style.width = "0%";
  gifStatus.textContent = "Preparing…";

  try {
    const result = await videoToGif(
      gifFile,
      options,
      (ratio) => { gifProgressFill.style.width = `${Math.round(ratio * 100)}%`; },
      (msg) => { gifStatus.textContent = msg; },
    );

    const url = URL.createObjectURL(result.blob);
    gifPreview.src = url;
    gifDownload.href = url;
    gifDownload.download = result.fileName;
    gifResultMeta.textContent =
      `${result.fileName} · ${formatBytes(result.blob.size)}`;

    gifProgress.classList.add("hidden");
    gifResult.classList.remove("hidden");
  } catch (err) {
    console.error(err);
    gifProgress.classList.add("hidden");
    const msg = err instanceof Error ? err.message : String(err);
    showError(gifError, `Error: ${msg}`);
  } finally {
    gifConvert.disabled = false;
  }
});

gifReset.addEventListener("click", () => {
  gifFileInput.value = "";
  setGifFile(null);
});

/* =================== Image conversion =================== */

const convFileInput = $<HTMLInputElement>("#conv-files");
const convDrop = $("#conv-drop");
const convBrowse = $<HTMLButtonElement>("#conv-browse");
const convFormat = $<HTMLSelectElement>("#conv-format");
const convQuality = $<HTMLInputElement>("#conv-quality");
const convConvert = $<HTMLButtonElement>("#conv-convert");
const convError = $("#conv-error");
const convProgress = $("#conv-progress");
const convProgressFill = $<HTMLDivElement>("#conv-progress-fill");
const convStatus = $("#conv-status");
const convResults = $("#conv-results");
const convPreviewGrid = $("#conv-preview-grid");
const convDropText = convDrop.querySelector("p") as HTMLParagraphElement;
const convDropTextDefault = convDropText.innerHTML;

const PREVIEW_THUMB_CAP = 24;

let convFiles: File[] = [];
let convPreviewUrls: string[] = [];

function clearConvPreviews(): void {
  for (const url of convPreviewUrls) URL.revokeObjectURL(url);
  convPreviewUrls = [];
  convPreviewGrid.innerHTML = "";
  convPreviewGrid.classList.add("hidden");
}

function setConvFiles(files: File[]): void {
  convFiles = files;
  convConvert.disabled = files.length === 0;
  convResults.classList.add("hidden");
  convResults.innerHTML = "";
  convError.classList.add("hidden");
  convProgress.classList.add("hidden");

  clearConvPreviews();

  if (files.length > 0) {
    convDropText.innerHTML =
      `<strong>${files.length}</strong> file${files.length === 1 ? "" : "s"} ready`;

    const shown = files.slice(0, PREVIEW_THUMB_CAP);
    for (const file of shown) {
      const url = URL.createObjectURL(file);
      convPreviewUrls.push(url);
      const img = document.createElement("img");
      img.src = url;
      img.alt = file.name;
      img.title = file.name;
      convPreviewGrid.appendChild(img);
    }
    if (files.length > PREVIEW_THUMB_CAP) {
      const more = document.createElement("div");
      more.className = "preview-more";
      more.textContent = `+${files.length - PREVIEW_THUMB_CAP}`;
      more.title = `${files.length - PREVIEW_THUMB_CAP} more file(s) not previewed`;
      convPreviewGrid.appendChild(more);
    }

    convPreviewGrid.classList.remove("hidden");
  } else {
    convDropText.innerHTML = convDropTextDefault;
  }
}

convBrowse.addEventListener("click", (e) => {
  e.stopPropagation();
  convFileInput.click();
});
convDrop.addEventListener("click", () => convFileInput.click());
convFileInput.addEventListener("change", () => {
  if (convFileInput.files) setConvFiles(Array.from(convFileInput.files));
});
wireDropzone(
  convDrop,
  (files) => setConvFiles(files),
  (f) => f.type.startsWith("image/"),
);

convConvert.addEventListener("click", async () => {
  if (convFiles.length === 0) return;

  const format = convFormat.value as OutputFormat;
  const quality = clamp(parseFloat(convQuality.value), 1, 100, 92);

  convConvert.disabled = true;
  convResults.classList.add("hidden");
  convResults.innerHTML = "";
  convError.classList.add("hidden");
  convProgress.classList.remove("hidden");

  const results: Awaited<ReturnType<typeof convertImage>>[] = [];
  let failed = 0;

  for (let i = 0; i < convFiles.length; i++) {
    const file = convFiles[i];
    convStatus.textContent = `Converting ${i + 1} / ${convFiles.length}: ${file.name}`;
    convProgressFill.style.width = `${Math.round(((i + 1) / convFiles.length) * 100)}%`;
    try {
      results.push(await convertImage(file, { format, quality }));
    } catch (err) {
      console.error(err);
      failed++;
    }
    // Let the browser breathe between images.
    await new Promise((r) => setTimeout(r, 0));
  }

  convProgress.classList.add("hidden");

  if (results.length === 0) {
    showError(convError, "No images could be converted.");
    convConvert.disabled = false;
    return;
  }

  for (const r of results) {
    const row = document.createElement("div");
    row.className = "result-row";
    const url = URL.createObjectURL(r.blob);
    row.innerHTML =
      `<span class="name">${escapeHtml(r.fileName)}</span>` +
      `<span class="size">${formatBytes(r.originalSize)} → ${formatBytes(r.outputSize)}</span>` +
      `<a href="${url}" download="${escapeHtml(r.fileName)}">Download</a>`;
    convResults.appendChild(row);
  }

  if (failed > 0) {
    const note = document.createElement("div");
    note.className = "error";
    note.textContent = `${failed} file${failed === 1 ? "" : "s"} could not be converted.`;
    convResults.appendChild(note);
  }

  convResults.classList.remove("hidden");
  convStatus.textContent = `Done - ${results.length} file${results.length === 1 ? "" : "s"} converted.`;
  convConvert.disabled = false;
});