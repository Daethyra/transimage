# transimage - image format conversion

## Description
`transimage` is a Python package and CLI tool for converting images between different formats using the Pillow library. It supports conversions between JPG, PNG, BMP, and WebP formats.

>> send your PR based god🙏🏻

## Features
- Convert images between JPG, PNG, BMP, and WebP formats
- Batch conversion of multiple images
- Simple command-line interface
- Skips conversion if the input and output formats are the same

## Usage

#### Dependencies
- Pillow >= 11.0.0
- Poetry

#### Setup
To set up the development environment:

1. Clone the repository
2. Install PDM if you haven't already: `pip install poetry` or `pipx install poetry`
3. Install dependencies(including dev tools): `poetry install`
4. Convert images: `poetry run python -m transimage ./input_image.jpg ./output_image.png png`

### Using `transimage` directly as a CLI tool (Recommended)

Once you've cloned the repository and run `poetry install`, the package is installed in the Poetry‑managed virtual environment. You can run it directly without activating anything: `poetry run python -m transimage <input_path> <output_path> <output_format>`

**Input target may be a single file or directory.**

- `<input_path>`: Path to the input image file or directory
- `<output_path>`: Path to save the converted image(s)
- `<output_format>`: Desired output format (jpg, png, bmp, or webp)

### Using the transimage package in your own projects

To use the package programmatically, first ensure you're inside the project's virtual environment (via poetry shell or by prefixing commands with poetry run).

Then, import the necessary functions:

`from transimage import collect_images, ImageConverter`

To convert a single image, use the ImageConverter class directly:

```python
converter = ImageConverter('path/to/input/image.jpg', 'path/to/output/image.png', 'png')
converter.convert()
```

#### Batch Conversions

For batch conversion, you can pass in directories as arguments instead of individual image paths. Then, use the collect_images function and loop through the results:

```python
from transimage import collect_images, ImageConverter
import os

input_directory = 'path/to/input/directory'
output_directory = 'path/to/output/directory'
output_format = 'png'

image_files = collect_images(input_directory)

for input_path in image_files:
    filename = os.path.basename(input_path)
    name, _ = os.path.splitext(filename)
    output_path = os.path.join(output_directory, f"{name}.{output_format}")
    convert_image(input_path, output_path, output_format)
```

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Contributing 
Please submit issues regarding any oversight you see. Pull requests for improvements are welcome.

### Set up
1. Install the developer dependencies: poetry install (dev deps are included by default)
2. Add your changes
3. Test your code: poetry run pytest tests/
4. Format and lint:
   - Format: poetry run black src/transimage tests
   - Lint: poetry run flake8 src/transimage tests
   - Run all together: poetry run black src/transimage tests && poetry run flake8 src/transimage tests && poetry run pytest tests
5. Rise and repeat until finished.

## Version
2.0.0
