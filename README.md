# transimage - image format conversion and GIF creation

## Description
`transimage` is a Python package and CLI tool for converting images between different formats and creating GIFs from image sequences, directories, or video files. It uses Pillow for image operations and OpenCV for video frame extraction.

>> send your PR based god🙏🏻

## Features
- Convert images between JPG, PNG, BMP, and WebP formats
- Batch conversion of multiple images or entire directories
- Create GIFs from a list of images, a directory of images, or a video file
  - Configurable GIF parameters: FPS, size, crop, loop, and video trim
  - Preserves aspect ratio on resize and handles transparency
- Simple command-line interface with subcommands
- Skips conversion if the input and output formats are the same

## Dependencies
- Pillow >= 11.0.0
- Poetry

Optional dependency for creating GIFs:
- opencv-python-headless

## Setup

### Development Environment

1. Clone the repository
2. Install Poetry: `pip install poetry` or `pipx install poetry`
3. Install all dependencies: `poetry install`
4. (Optional) For video support: `poetry install --extras opencv`

## Usage

All commands are run from the project root using Poetry’s virtual environment. Replace `poetry run python -m transimage` with `transimage` if you installed the package globally.

### Image Conversion

Convert a single image or all images in a directory:

    poetry run python -m transimage convert <input_path> <output_path> <output_format>

- `<input_path>`: Path to a single image file or a directory of images
- `<output_path>`: Directory where converted images will be saved (do not include file name)
- `<output_format>`: Target format (jpg, png, bmp, webp)

#### Examples

    poetry run python -m transimage convert ./photo.jpg ./output png
    poetry run python -m transimage convert ./images/ ./converted webp

### GIF Creation

Create a GIF from images or video:

    poetry run python -m transimage gif <input> -o <output.gif> [options]

- `<input>`: A directory path, a video file path, or a list of image file paths (list them after the command)
- `-o, --output`: Output GIF file path (required)

#### Options

| Option           | Type   | Default | Description                                                  |
|------------------|--------|---------|--------------------------------------------------------------|
| `--fps`          | float  | 24      | Frames per second                                            |
| `--size`         | int int| -       | Max width and height (aspect ratio preserved)                |
| `--crop`         | int int int int | - | Crop box: left top right bottom                         |
| `--loop`         | int    | 0       | Loop count (0 = infinite)                                    |
| `--start-time`   | float  | -       | Start time in seconds (video only)                           |
| `--end-time`     | float  | -       | End time in seconds (video only)                             |
| `--skip-frames`  | int    | 1       | Only use every Nth frame (video only)                        |

#### Examples

From a directory of images (sorted by name):

    poetry run python -m transimage gif ./frames -o movie.gif --fps 12 --size 640 480

From a list of explicit image files:

    poetry run python -m transimage gif a.jpg b.jpg c.jpg -o combined.gif --fps 2 --loop 0

From a video file (requires the `opencv` extra):

    poetry run python -m transimage gif video.mp4 -o clip.gif --fps 15 --start-time 2.5 --end-time 5 --size 320 240

To preserve real-time speed from a video, adjust `--skip-frames` so that `fps / skip_frames` roughly equals the original video’s frame rate. For a 30 fps video, `--fps 18 --skip-frames 2` gives a natural-looking GIF.

## Programmatic Usage

Inside a script or interactive session, you can use the package directly after installing it in your environment.

Import the needed functions:

    from transimage import ImageConverter, convert_image, collect_images, GIFCreator, create_gif

### Image Conversion

    converter = ImageConverter('input.jpg', 'output.png', 'png')
    converter.convert()

Batch conversion:

    import os
    from transimage import collect_images, convert_image

    input_dir = 'images/'
    output_dir = 'converted/'
    fmt = 'png'
    for img_path in collect_images(input_dir):
        name = os.path.splitext(os.path.basename(img_path))[0]
        out_path = os.path.join(output_dir, f"{name}.{fmt}")
        convert_image(img_path, out_path, fmt)

### GIF Creation

Using the convenience function:

    create_gif(
        input=['a.jpg', 'b.jpg', 'c.jpg'],   # or a directory path, or a video file path
        output='animation.gif',
        fps=10,
        size=(320, 240),
        loop=0
    )

Or with the class for more control:

    creator = GIFCreator(
        sources='video.mp4',
        output_path='clip.gif',
        fps=15,
        size=(480, 360),
        start_time=2.0,
        end_time=5.0,
        skip_frames=2
    )
    creator.create()

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
