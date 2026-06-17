"""
Main entry point for transimage: image conversion and GIF creation.
"""

import argparse
import os
from typing import List

from transimage.image_collector import collect_images
from transimage.image_converter import convert_image
from transimage.gif_creator import create_gif


def process_images(input_path: str, output_path: str, output_format: str) -> List[str]:
    """
    Process images based on whether the input path is a single image or a directory.
    """
    if not os.path.exists(input_path):
        raise ValueError(f"Input path does not exist: {input_path}")

    converted_images = []

    if os.path.isfile(input_path):
        # Single image processing
        output_filename = (
            f"{os.path.splitext(os.path.basename(input_path))[0]}.{output_format}"
        )
        output_file_path = os.path.join(output_path, output_filename)
        convert_image(input_path, output_file_path, output_format)
        if os.path.exists(output_file_path):
            converted_images.append(output_file_path)
    elif os.path.isdir(input_path):
        # Directory processing
        os.makedirs(output_path, exist_ok=True)
        image_files = collect_images(input_path)

        for file_path in image_files:
            output_filename = (
                f"{os.path.splitext(os.path.basename(file_path))[0]}.{output_format}"
            )
            output_file_path = os.path.join(output_path, output_filename)
            try:
                convert_image(file_path, output_file_path, output_format)
                if os.path.exists(output_file_path):
                    converted_images.append(output_file_path)
            except ValueError as e:
                print(f"Error converting {file_path}: {str(e)}")

    return converted_images


def main() -> None:
    """Entry point for the transimage command-line tool."""
    parser = argparse.ArgumentParser(description="TransImage: convert images or create GIFs")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # ---------- convert subcommand ----------
    convert_parser = subparsers.add_parser("convert", help="Convert image formats")
    convert_parser.add_argument("input_path", help="Input image or directory")
    convert_parser.add_argument("output_path", help="Output directory (not a file name)")
    convert_parser.add_argument("output_format", help="Target format (jpg, png, bmp, webp)")

    # ---------- gif subcommand ----------
    gif_parser = subparsers.add_parser("gif", help="Create a GIF from images or video")
    gif_parser.add_argument(
        "input",
        help="Input: directory, video file, or multiple image paths (list them after the command)",
    )
    gif_parser.add_argument("-o", "--output", required=True, help="Output GIF file path")
    gif_parser.add_argument("--fps", type=float, default=24, help="Frames per second (default: 10)")
    gif_parser.add_argument(
        "--size", nargs=2, type=int, metavar=("WIDTH", "HEIGHT"),
        help="Resize frames to fit inside WIDTHxHEIGHT (aspect ratio kept)"
    )
    gif_parser.add_argument(
        "--crop", nargs=4, type=int, metavar=("L", "T", "R", "B"),
        help="Crop box: left top right bottom"
    )
    gif_parser.add_argument("--loop", type=int, default=0, help="Loop count (0 = infinite)")
    gif_parser.add_argument("--start-time", type=float, default=None, help="Start time in seconds (video only)")
    gif_parser.add_argument("--end-time", type=float, default=None, help="End time in seconds (video only)")
    gif_parser.add_argument("--skip-frames", type=int, default=1, help="Take every Nth frame (video only)")

    # parse_known_args allows extra positional arguments (image files) to be collected
    args, unknown = parser.parse_known_args()

    if args.command == "convert":
        try:
            converted_files = process_images(args.input_path, args.output_path, args.output_format)
            print(f"\nSuccessfully operated {len(converted_files)} images.")
        except ValueError as e:
            print(f"Error: {str(e)}")

    elif args.command == "gif":
        # Determine input source
        if unknown:
            # user passed extra file names -> list of images
            input_src = [args.input] + unknown
        else:
            # single argument: could be directory or video
            input_src = args.input

        try:
            create_gif(
                input=input_src,
                output=args.output,
                fps=args.fps,
                size=tuple(args.size) if args.size else None,
                crop=tuple(args.crop) if args.crop else None,
                loop=args.loop,
                start_time=args.start_time,
                end_time=args.end_time,
                skip_frames=args.skip_frames,
            )
            print("GIF created successfully.")
        except Exception as e:
            print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()