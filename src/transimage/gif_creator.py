"""
Module for creating GIFs from images, image directories, or video files.
"""

import os
from typing import List, Optional, Union, Tuple

from PIL import Image

from .image_collector import collect_images


class GIFCreator:
    def __init__(
        self,
        sources: Union[List[str], str],
        output_path: str,
        fps: float = 10,
        size: Optional[Tuple[int, int]] = None,          # (width, height) – frames fit inside, keeping ratio
        crop: Optional[Tuple[int, int, int, int]] = None, # (left, top, right, bottom)
        loop: int = 0,                                   # 0 = infinite loop
        duration: Optional[int] = None,                  # per‑frame display in ms (overrides fps)
        resize_method: int = Image.LANCZOS,
        skip_frames: int = 1,                            # for video: take every Nth frame
        start_time: Optional[float] = None,              # seconds, video only
        end_time: Optional[float] = None,                # seconds, video only
        colors: int = 256,                               # control maximum bitmap depth
        dither: bool = True,                             # whether to dither. kinda sounds like a dance move
    ):
        if not 2 <= colors <= 256:
            raise ValueError(
                f"colors must be between 2 and 256, got {colors}"
            )
        self.sources = sources
        self.output_path = output_path
        self.fps = fps
        self.size = size
        self.crop = crop
        self.loop = loop
        self.duration = duration or int(1000 / fps)
        self.resize_method = resize_method
        self.skip_frames = skip_frames
        self.start_time = start_time
        self.end_time = end_time
        self.colors = colors
        self.dither = dither

    def _load_images_from_video(self, video_path: str) -> List[Image.Image]:
        """Extract frames from a video file using OpenCV."""
        try:
            import cv2
        except ImportError:
            raise ImportError(
                "To process video files, install opencv-python-headless"
            )

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")

        fps_video = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Calculate start / end frames
        start_frame = 0
        end_frame = total_frames
        if self.start_time is not None:
            start_frame = max(0, int(self.start_time * fps_video))
        if self.end_time is not None:
            end_frame = min(total_frames, int(self.end_time * fps_video))

        frames = []
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret or frame_idx >= end_frame:
                break
            if frame_idx >= start_frame and (frame_idx - start_frame) % self.skip_frames == 0:
                # Convert BGR (OpenCV) to RGB for Pillow
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                frames.append(pil_image)
            frame_idx += 1

        cap.release()
        return frames

    def _process_frames(self, images: List[Image.Image]) -> List[Image.Image]:
        """Resize, crop, and ensure all frames are in RGB mode."""
        processed = []
        for img in images:
            # Resize while keeping aspect ratio (thumbnail fits inside the box)
            if self.size:
                img = img.copy()
                img.thumbnail(self.size, self.resize_method)
            # Crop if a box is given
            if self.crop:
                img = img.crop(self.crop)
            # Ensure image is in RGB mode (GIF doesn't store alpha like PNG)
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P" and "transparency" in img.info:
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")
            processed.append(img)
        return processed
    
    def _quantize_frames(self, frames: List[Image.Image]) -> List[Image.Image]:
        """Reduce each frame to the selected palette using the configured dither setting."""
        if self.colors >= 256:
            return frames

        quantized = []
        dither_method = Image.Dither.FLOYDSTEINBERG if self.dither else Image.Dither.NONE
        for img in frames:
            # quantize() returns a new image, converts to 'P' mode with the given palette
            q = img.quantize(
                colors=self.colors,
                method=Image.MEDIANCUT,      # median cut is fast and effective
                dither=dither_method,
            )
            quantized.append(q)
        return quantized

    def create(self) -> None:
        """Generate the GIF and save it."""
        # 1. Gather images based on source type
        if isinstance(self.sources, str):
            path = self.sources
            if not os.path.exists(path):
                raise FileNotFoundError(f"Source path not found: {path}")
            if os.path.isdir(path):
                # sorted to have a predictable order
                file_paths = sorted(collect_images(path))
                images = [Image.open(p) for p in file_paths]
            else:
                # Assume it's a video file
                video_exts = (".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv")
                if any(path.lower().endswith(ext) for ext in video_exts):
                    images = self._load_images_from_video(path)
                else:
                    raise ValueError(
                        "Single source path is not a recognized video file or directory."
                    )
        elif isinstance(self.sources, list):
            # List of image file paths
            images = [Image.open(p) for p in self.sources]
        else:
            raise TypeError("sources must be a list of paths or a single path (directory/video).")

        if not images:
            raise ValueError("No frames collected. Check your input.")

        # 2. Process all frames (resize, crop, convert to RGB)
        frames = self._process_frames(images)
        
        # Quantize frames if color limit is set
        frames = self._quantize_frames(frames)

        # 3. Save as GIF
        frames[0].save(
            self.output_path,
            save_all=True,
            append_images=frames[1:],
            duration=self.duration,
            loop=self.loop,
            optimize=True,
        )
        print(f"GIF saved to {self.output_path} ({len(frames)} frames)")


def create_gif(
    input: Union[List[str], str],
    output: str,
    fps: float = 10,
    size: Optional[Tuple[int, int]] = None,
    crop: Optional[Tuple[int, int, int, int]] = None,
    loop: int = 0,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    skip_frames: int = 1,
    colors: int = 256,
    dither: bool = True,
) -> None:
    """
    Convenience function to create a GIF with default parameters.

    Args:
        input: List of image paths, a directory path, or a video file path.
        output: Output GIF file path.
        fps: Frames per second.
        size: (width, height) to resize frames (aspect ratio preserved).
        crop: (left, upper, right, lower) crop box.
        loop: Number of loops (0 = infinite).
        start_time: Start time in seconds (video only).
        end_time: End time in seconds (video only).
        skip_frames: Only use every Nth frame (video only).
        colors: Maximum number of colors in the GIF palette (2‑256, default 256).
        dither: Whether to apply dithering (True for Floyd‑Steinberg(default), False to disable).
    """
    creator = GIFCreator(
        sources=input,
        output_path=output,
        fps=fps,
        size=size,
        crop=crop,
        loop=loop,
        start_time=start_time,
        end_time=end_time,
        skip_frames=skip_frames,
        colors=colors,
        dither=dither,
    )
    creator.create()