"""
This module provides functionality to collect images from a directory.
"""

import os
from typing import List

from .image_converter import ImageConverter


def collect_images(input_dir: str) -> List[str]:
    """
    Collects all supported image files from the input directory.

    Args:
        input_dir (str): Path to the input directory containing images.

    Returns:
        List[str]: A list of paths to the supported image files.

    Raises:
        ValueError: If the input directory does not exist.
    """
    if not os.path.isdir(input_dir):
        raise ValueError(f"Input directory does not exist: {input_dir}")

    supported_extensions = set(
        ImageConverter.SUPPORTED_CONVERSIONS.keys()
    )  # {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    image_files = []

    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)
        if (
            os.path.isfile(file_path)
            and os.path.splitext(filename)[1].lower() in supported_extensions
        ):
            image_files.append(file_path)

    return image_files
