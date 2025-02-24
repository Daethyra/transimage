import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

import unittest
import tempfile
import shutil
from PIL import Image
from pil_image_converter.image_converter import ImageConverter, convert_image


class TestImageConverter(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.input_jpg = os.path.join(self.test_dir, "test.jpg")
        self.output_png = os.path.join(self.test_dir, "test.png")
        self.output_jpg = os.path.join(self.test_dir, "test_output.jpg")

        # Create a test JPEG image
        with Image.new("RGB", (100, 100), color="red") as img:
            img.save(self.input_jpg)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_convert_jpg_to_png(self):
        converter = ImageConverter(self.input_jpg, self.output_png, "png")
        converter.convert()
        self.assertTrue(os.path.exists(self.output_png))
        with Image.open(self.output_png) as img:
            self.assertEqual(img.format, "PNG")

    def test_convert_jpg_to_jpg(self):
        converter = ImageConverter(self.input_jpg, self.output_jpg, "jpg")
        converter.convert()
        self.assertFalse(
            os.path.exists(self.output_jpg)
        )  # Should not create a new file

    def test_unsupported_input_format(self):
        invalid_input = os.path.join(self.test_dir, "test.txt")
        with open(invalid_input, "w") as f:
            f.write("This is not an image file")
        with self.assertRaises(ValueError):
            converter = ImageConverter(invalid_input, self.output_png, "png")
            converter.convert()

    def test_unsupported_conversion(self):
        invalid_output = os.path.join(self.test_dir, "test.gif")
        with self.assertRaises(ValueError):
            converter = ImageConverter(self.input_jpg, invalid_output, "gif")
            converter.convert()

    def test_same_input_output_format(self):
        output_jpg = os.path.join(self.test_dir, "test_same.jpg")
        converter = ImageConverter(self.input_jpg, output_jpg, "jpg")
        converter.convert()
        self.assertFalse(os.path.exists(output_jpg))  # Should not create a new file

    def test_convert_image_function(self):
        convert_image(self.input_jpg, self.output_png, "png")
        self.assertTrue(os.path.exists(self.output_png))
        with Image.open(self.output_png) as img:
            self.assertEqual(img.format, "PNG")

    def test_supported_conversions_string(self):
        supported_str = ImageConverter.supported_conversions()
        self.assertIsInstance(supported_str, str)
        self.assertIn("JPEG", supported_str)
        self.assertIn("PNG", supported_str)
        self.assertIn("BMP", supported_str)
        self.assertIn("WebP", supported_str)


if __name__ == "__main__":
    unittest.main()
