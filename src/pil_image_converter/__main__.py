"""
Main module for image conversion. Handles both single image and directory processing.
"""

import argparse
import os
from typing import List

from pil_image_converter.image_collector import collect_images
from pil_image_converter.image_converter import convert_image


def process_images(input_path: str, output_path: str, output_format: str) -> List[str]:
    """
    Process images based on whether the input path is a single image or a directory.

    Args:
        input_path (str): Path to the input image file or directory.
        output_path (str): Path to save the converted image file or directory.
        output_format (str): Desired output format (e.g., 'jpg', 'png', 'bmp', 'webp').

    Returns:
        List[str]: A list of paths to the converted images.

    Raises:
        ValueError: If the input path does not exist.
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert images to a specified format."
    )
    parser.add_argument("input_path", help="Path to input image or directory")
    parser.add_argument("output_path", help="Path to output directory. Do not include file name.")
    parser.add_argument(
        "output_format", help="Desired output format (jpg, png, bmp, webp)"
    )
    args = parser.parse_args()

    try:
        converted_files = process_images(
            args.input_path, args.output_path, args.output_format
        )
        print(f"Successfully converted {len(converted_files)} images.")
    except ValueError as e:
        print(f"Error: {str(e)}")
