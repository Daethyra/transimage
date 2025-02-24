# Pillow Image-Format Converter

## Description
`pil_image_converter` is a Python package for converting images between different formats using the Pillow library. It supports conversions between JPG, PNG, BMP, and WebP formats.

Contributions always welcome!

## Features
- Convert images between JPG, PNG, BMP, and WebP formats
- Batch conversion of multiple images
- Simple command-line interface
- Skips conversion if the input and output formats are the same

## Usage

#### Dependencies
- Pillow >= 11.0.0

#### Setup
To set up the development environment:

1. Clone the repository
2. Install PDM if you haven't already: `pip install pdm`
3. Install dependencies: `pdm install`
4. Convert images: `python main.py ./input_image.jpg ./output_image.png png`

### Using `main.py` directly as a CLI tool (Recommended)

If you've cloned the repository or downloaded the source code, you can use the `main.py` file directly:

1. Navigate to the directory containing `main.py`
2. Run the following command:

`python main.py <input_path> <output_path> <output_format>`

Example:

`python main.py ./input_image.jpg ./output_image.png png`

For batch conversion:

`python main.py ./input_directory ./output_directory png`

**Note:** You should use quotations for paths containing spaces.
-> Ex.: `python main.py "./input directory" "./output directory" jpg`


### Using the pil_image_converter package

You can use the Image_Converter package directly from the command line:

`python -m pil_image_converter <input_path> <output_path> <output_format>`

- `<input_path>`: Path to the input image file or directory
- `<output_path>`: Path to save the converted image(s)
- `<output_format>`: Desired output format (jpg, png, bmp, or webp)

Example:

`python -m pil_image_converter ./input_image.jpg ./output_image.png png`

For batch conversion, provide a directory as the input path:

`python -m pil_image_converter ./input_directory ./output_directory png`

### Using pil_image_converter in your own projects

1. First, ensure you're working within a virtual environment with PDM:

   `pdm install`

2. In your Python script, import the necessary functions:

```python
from pil_image_converter import collect_images, ImageConverter
```

To convert a single image, use the ImageConverter class directly:

```python
converter = ImageConverter('path/to/input/image.jpg', 'path/to/output/image.png', 'png')
converter.convert()
```

For batch conversion, you can pass in directories as arguments instead of individual image paths. Then, use the collect_images function and loop through the results:

```python
from pil_image_converter import collect_images, ImageConverter

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

## Version
3.0.0
