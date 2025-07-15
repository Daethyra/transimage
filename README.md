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

#### Setup
To set up the development environment:

1. Clone the repository
2. Install PDM if you haven't already: `pip install pdm`
3. Install dependencies: `pdm install`
4. Convert images: `python src/__main__.py ./input_image.jpg ./output_image.png png`

### Using `__main__.py` directly as a CLI tool (Recommended)

Once you've cloned the repository or downloaded the source code, you can use the `__main__.py` file directly by using the following: `python __main__.py <input_path> <output_path> <output_format>`

**Input target may be a single file or directory.**

- `<input_path>`: Path to the input image file or directory
- `<output_path>`: Path to save the converted image(s)
- `<output_format>`: Desired output format (jpg, png, bmp, or webp)

### Using the transimage package in your own projects

You may test the transimage package is properly installed by running it directly from the command line: `python -m transimage <input_path> <output_path> <output_format>`

1. First, ensure you're working within a virtual environment with PDM:

   `pdm install`

2. In your Python script, import the necessary functions:

```python
from transimage import collect_images, ImageConverter
```

To convert a single image, use the ImageConverter class directly:

```python
converter = ImageConverter('path/to/input/image.jpg', 'path/to/output/image.png', 'png')
converter.convert()
```

For batch conversion, you can pass in directories as arguments instead of individual image paths. Then, use the collect_images function and loop through the results:

```python
from transimage import collect_images, ImageConverter

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
Like I said, send your PR. Based. God.

### Set up
1. Install the developer dependencies: `pdm install -G dev`
2. Add your changes
3. Test your code(`pdm run pytest tests/`)
4. Iterate, repeat until finished.
5. Run the `all` script to lint and format the code: `pdm run all`

## Version
1.0.0
