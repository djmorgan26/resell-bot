#!/usr/bin/env python3
"""Convert HEIC images to JPEG for marketplace listings.

Usage:
    python3 convert_heic.py <input_dir> <output_dir> [--quality 90] [--max-size 2000]

Converts all .heic/.HEIC files in input_dir to JPEG in output_dir.
Also copies any existing .jpeg/.jpg/.png files to output_dir.
Optionally resizes images if they exceed max-size on the longest side.
"""

import sys
import os
import argparse
from pathlib import Path

def convert_heic_to_jpeg(input_dir, output_dir, quality=90, max_size=None):
    """Convert all HEIC files in input_dir to JPEG in output_dir."""
    from PIL import Image
    import pillow_heif

    # Register HEIF opener with Pillow
    pillow_heif.register_heif_opener()

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Collect all image files
    image_extensions = {'.heic', '.heif', '.jpeg', '.jpg', '.png'}
    files = [f for f in input_path.iterdir()
             if f.suffix.lower() in image_extensions and not f.name.startswith('.')]

    if not files:
        print(f"No image files found in {input_dir}")
        return []

    converted = []
    for f in sorted(files):
        try:
            img = Image.open(f)

            # Auto-orient based on EXIF
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)

            # Resize if needed
            if max_size and max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.LANCZOS)

            # Convert to RGB if necessary (handles RGBA PNGs, etc.)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Output as JPEG
            out_name = f.stem + '.jpeg'
            out_file = output_path / out_name
            img.save(out_file, 'JPEG', quality=quality, optimize=True)

            converted.append({
                'source': str(f),
                'output': str(out_file),
                'size': img.size,
                'file_size_kb': round(out_file.stat().st_size / 1024, 1)
            })
            print(f"  Converted: {f.name} → {out_name} ({img.size[0]}x{img.size[1]}, {converted[-1]['file_size_kb']}KB)")

        except Exception as e:
            print(f"  Error converting {f.name}: {e}")

    print(f"\nConverted {len(converted)}/{len(files)} files to {output_dir}")
    return converted


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert HEIC images to JPEG')
    parser.add_argument('input_dir', help='Directory containing HEIC/image files')
    parser.add_argument('output_dir', help='Output directory for JPEG files')
    parser.add_argument('--quality', type=int, default=90, help='JPEG quality (1-100)')
    parser.add_argument('--max-size', type=int, default=None,
                        help='Max dimension in pixels (longest side)')

    args = parser.parse_args()
    convert_heic_to_jpeg(args.input_dir, args.output_dir, args.quality, args.max_size)
