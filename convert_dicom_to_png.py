"""
Convert DICOM files to PNG for use in MRI Training Platform
Usage: python convert_dicom_to_png.py

Place your .dcm files in: dicom_files/
Outputs PNG files to: media/questions/
"""

import os
import sys
from pathlib import Path

try:
    import pydicom
    from PIL import Image
    import numpy as np
except ImportError:
    print("ERROR: Required libraries not installed!")
    print("\nInstall with:")
    print("pip install pydicom pillow numpy")
    sys.exit(1)


def convert_dicom_to_png(dicom_path, output_path, apply_window=True):
    """
    Convert a single DICOM file to PNG
    
    Args:
        dicom_path: Path to .dcm file
        output_path: Path for output .png file
        apply_window: Apply window/level settings for better contrast
    """
    try:
        # Read DICOM file
        dicom = pydicom.dcmread(dicom_path)
        
        # Get pixel array
        pixel_array = dicom.pixel_array
        
        # Apply window/level if available and requested
        if apply_window:
            try:
                # Try to get window settings from DICOM
                window_center = dicom.WindowCenter
                window_width = dicom.WindowWidth
                
                # Handle multiple windows (take first one)
                if isinstance(window_center, pydicom.multival.MultiValue):
                    window_center = window_center[0]
                if isinstance(window_width, pydicom.multival.MultiValue):
                    window_width = window_width[0]
                
                # Apply windowing
                img_min = window_center - window_width // 2
                img_max = window_center + window_width // 2
                pixel_array = np.clip(pixel_array, img_min, img_max)
                
            except AttributeError:
                print(f"  No window settings found, using auto-contrast")
        
        # Normalize to 0-255
        pixel_array = pixel_array - np.min(pixel_array)
        pixel_array = pixel_array / np.max(pixel_array)
        pixel_array = (pixel_array * 255).astype(np.uint8)
        
        # Convert to PIL Image
        image = Image.fromarray(pixel_array)
        
        # Convert to RGB if grayscale
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize to reasonable dimensions if too large
        max_size = (1024, 1024)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            print(f"  Resized to: {image.size}")
        
        # Save as PNG
        image.save(output_path, 'PNG', optimize=True)
        print(f"✓ Converted: {dicom_path.name} → {output_path.name}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to convert {dicom_path.name}: {str(e)}")
        return False


def batch_convert(input_dir='dicom_files', output_dir='media/questions'):
    """
    Convert all DICOM files in input directory to PNG in output directory
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Create directories if they don't exist
    input_path.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all DICOM files
    dicom_files = list(input_path.glob('*.dcm')) + list(input_path.glob('*.DCM'))
    
    if not dicom_files:
        print(f"\n⚠️  No DICOM files found in {input_dir}/")
        print(f"Place your .dcm files there and run again.")
        return
    
    print(f"\nFound {len(dicom_files)} DICOM files")
    print(f"Converting to PNG in {output_dir}/\n")
    
    success_count = 0
    
    for idx, dicom_file in enumerate(dicom_files, 1):
        # Generate output filename
        png_filename = f"brain_{idx:03d}.png"
        png_path = output_path / png_filename
        
        print(f"[{idx}/{len(dicom_files)}] Processing {dicom_file.name}...")
        
        if convert_dicom_to_png(dicom_file, png_path):
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"✓ Successfully converted: {success_count}/{len(dicom_files)} files")
    print(f"✓ PNG files saved to: {output_dir}/")
    print(f"\nNext steps:")
    print(f"1. Check the PNG files in {output_dir}/")
    print(f"2. In Django admin, upload these PNG files to your DICOM questions")
    print(f"3. Use 'Question Image' field (not 'DICOM file' field)")


def convert_single_file(dicom_path, png_path=None):
    """
    Convert a single DICOM file
    
    Usage:
        python convert_dicom_to_png.py path/to/file.dcm
    """
    dicom_path = Path(dicom_path)
    
    if png_path is None:
        png_path = dicom_path.with_suffix('.png')
    else:
        png_path = Path(png_path)
    
    print(f"Converting {dicom_path} → {png_path}")
    
    if convert_dicom_to_png(dicom_path, png_path):
        print(f"\n✓ Success! PNG saved to: {png_path}")
        print(f"\nUpload this file in Django admin:")
        print(f"Question → Question Image field")
    else:
        print(f"\n✗ Conversion failed")


if __name__ == '__main__':
    print("="*60)
    print("DICOM to PNG Converter for MRI Training Platform")
    print("="*60)
    
    if len(sys.argv) > 1:
        # Single file mode
        dicom_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        convert_single_file(dicom_file, output_file)
    else:
        # Batch mode
        batch_convert()
