import unittest
import sys
import os
import tempfile
import shutil

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from image_converter.image_collector import collect_images
from image_converter.image_converter import ImageConverter


class TestImageCollector(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

        # Create some test files
        self.valid_images = ["test1.jpg", "test2.png", "test3.bmp", "test4.webp"]
        self.invalid_files = ["test5.txt", "test6.pdf", "test7"]

        for filename in self.valid_images + self.invalid_files:
            open(os.path.join(self.test_dir, filename), "a").close()

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.test_dir)

    def test_collect_images(self):
        # Test if the function collects only valid image files
        collected_images = collect_images(self.test_dir)

        self.assertEqual(len(collected_images), len(self.valid_images))

        for image in collected_images:
            self.assertTrue(os.path.basename(image) in self.valid_images)

    def test_non_existent_directory(self):
        # Test if the function raises a ValueError for a non-existent directory
        with self.assertRaises(ValueError):
            collect_images("/path/to/non/existent/directory")

    def test_empty_directory(self):
        # Test if the function returns an empty list for an empty directory
        empty_dir = tempfile.mkdtemp()
        self.assertEqual(collect_images(empty_dir), [])
        shutil.rmtree(empty_dir)

    def test_supported_extensions(self):
        # Test if the function only collects files with supported extensions
        collected_images = collect_images(self.test_dir)
        supported_extensions = set(ImageConverter.SUPPORTED_CONVERSIONS.keys())

        for image in collected_images:
            _, ext = os.path.splitext(image)
            self.assertIn(ext.lower(), supported_extensions)


if __name__ == "__main__":
    unittest.main()
