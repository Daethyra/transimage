"""
This module provides a class for converting images to different formats using Pillow. It also has a function to simplify implementing the conversion logic.
"""

import os

from PIL import Image


class ImageConverter:
    SUPPORTED_CONVERSIONS = {
        **{ext: {".jpg", ".png", ".bmp", ".webp"}
           for ext in [".jpg", ".jpeg"]},
        ".png": {".jpg", ".png", ".bmp", ".webp"},
        ".bmp": {".jpg", ".png", ".bmp", ".webp"},
        ".webp": {".jpg", ".png", ".bmp", ".webp"},
    }

    def __init__(self, input_path: str, output_path: str, output_format: str, jpg_quality=95):
        """
        Initializes a new instance of the ImageConverter class.

        Args:
            input_path (str): Path to the input image file.
            output_path (str): Path to save the converted image file.
            output_format (str): Desired output format (e.g., 'png', 'jpg', 'bmp', 'webp').
        """
        self.input_path = input_path
        self.output_path = output_path
        self.output_format = output_format.lower()
        self.jpg_quality = jpg_quality

    def convert(self) -> None:
        """
        Converts an image to the desired format.

        Raises:
            ValueError: If the input file format is not supported or the conversion is not possible.
        """
        input_ext = os.path.splitext(self.input_path)[1].lower()
        output_ext = os.path.splitext(self.output_path)[1].lower()

        if input_ext not in self.SUPPORTED_CONVERSIONS:
            raise ValueError(
                f"Unsupported input file format: {input_ext}. {self.supported_conversions()}"
            )

        if output_ext not in self.SUPPORTED_CONVERSIONS[input_ext]:
            raise ValueError(
                f"Unsupported conversion: {input_ext} to {output_ext}. {self.supported_conversions()}"
            )

        if input_ext == output_ext:
            # If the input and output formats are the same, move the file instead of re-saving it
            self._move_or_error()
            print(
                f"Skipping conversion for {self.input_path} (already in {self.output_format} format)"
            )
            return
        else:
            # Handle JPG conversion separately
            if self.output_format.lower() == "jpg":
                self._convert_to_jpg(input_ext, output_ext)
            else:
                self._convert_image(input_ext, output_ext)

    def _convert_to_jpg(self, input_ext: str, output_ext: str) -> None:
        img = Image.open(self.input_path)

        # Ensure the output format is actually JPG
        if output_ext.lower() != "jpg":
            output_ext = "jpg"

        # Save transparency metadata for palette images w/ transparency
        if img.mode == "P" and img.info.get("transparency"):
            img = img.convert("RGBA")

        # Convert to RGB
        rgb_img = img.convert("RGB")

        # Save as JPG with quality 95 (adjust as needed)
        rgb_img.save(self.output_path, "JPEG", quality=self.jpg_quality)
        print(f"Successfully converted {self.input_path} to jpg.")

    def _convert_image(self, input_ext: str, output_ext: str) -> None:
        """
        Converts the input image to the specified output format using Pillow.
        """
        img = Image.open(self.input_path)
        img.save(self.output_path)
        print(f"Successfully converted {self.input_path} to {self.output_path}.")

    def _move_or_error(self) -> None:
        """
        If the input and output paths are the same, move the file instead of re-saving it.
        """
        if self.input_path != self.output_path:
            os.replace(self.input_path, self.output_path)
            print(
                f"Moved {self.input_path} to {self.output_format}"
            )
        else:
            raise ValueError(
                f"Input and output paths are the same: {self.input_path}. Please provide a different output path."
            )

    @staticmethod
    def supported_conversions() -> str:
        """
        Returns a string with the supported file formats and conversions.

        Returns:
            str: A string with the supported file formats and conversions.
        """
        return (
            "Supported file formats and conversions:\n"
            "JPG/JPEG: can be converted to JPG, PNG, BMP, WebP\n"
            "PNG: can be converted to JPEG, PNG, BMP, WebP\n"
            "BMP: can be converted to JPEG, PNG, BMP, WebP\n"
            "WebP: can be converted to JPEG, PNG, BMP, WebP"
        )


def convert_image(input_path: str, output_path: str, output_format: str) -> None:
    """
    Converts an image to the desired format.

    Args:
        input_path (str): Path to the input image file.
        output_path (str): Path to save the converted image file.
        output_format (str): Desired output format (e.g., 'png', 'jpg', 'bmp', 'webp').

    Raises:
        ValueError: If the input file format is not supported or the conversion is not possible.
    """
    converter = ImageConverter(input_path, output_path, output_format)
    converter.convert()
