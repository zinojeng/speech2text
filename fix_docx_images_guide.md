# Fix DOCX Images Guide

## Problem
Images are appearing as text paths like `[IMAGE: 1. GLP-1 RA/slide014t3m47.0s_ha7266061.jpg]` instead of actual images in the DOCX file.

## Solution

### Option 1: Use the Updated merge_transcript_multi_slides.py
The script has been updated to handle image paths directly. When you run it, it will now properly insert images that are referenced as file paths.

```bash
python merge_transcript_multi_slides.py transcript.txt slides.md --output output_name
```

### Option 2: Fix Existing DOCX Files
Use the `docx_image_fix.py` script to process existing DOCX files that have image text references:

```bash
# If images are in the same directory as the DOCX
python docx_image_fix.py your_document.docx

# If images are in a different directory
python docx_image_fix.py your_document.docx /path/to/image/directory
```

This will create a new file with `.fixed.docx` extension containing the actual images.

### Option 3: Manual Python Script
For custom processing, use this approach:

```python
from docx import Document
from docx.shared import Inches
import re
import os

def fix_docx_images(docx_path):
    doc = Document(docx_path)
    new_doc = Document()
    
    for para in doc.paragraphs:
        if '[IMAGE:' in para.text:
            # Extract image paths
            matches = re.findall(r'\[IMAGE:\s*([^\]]+)\]', para.text)
            for img_path in matches:
                if os.path.exists(img_path):
                    new_doc.add_picture(img_path, width=Inches(5.5))
                else:
                    new_doc.add_paragraph(f"[Missing: {img_path}]")
        else:
            # Copy regular paragraph
            new_para = new_doc.add_paragraph(para.text)
    
    new_doc.save('fixed_document.docx')
```

## How the Fix Works

1. **Pattern Detection**: The code now looks for `[IMAGE: path]` patterns where path can be:
   - A timestamp (original format): `[IMAGE: 3m47s]`
   - A file path (new format): `[IMAGE: folder/filename.jpg]`

2. **Path Resolution**: When a file path is detected, the code tries to find the image in:
   - The exact path specified
   - Relative to the current directory
   - Relative to the DOCX file location

3. **Image Insertion**: Found images are inserted with a width of 5.5 inches (adjustable)

## Troubleshooting

### Images Still Not Appearing
1. Check that image files exist at the specified paths
2. Verify image file permissions
3. Ensure image formats are supported (JPG, PNG)
4. Check the console/log output for specific error messages

### Path Issues
- Use forward slashes `/` even on Windows
- Ensure no extra spaces in the image references
- Try using absolute paths if relative paths don't work

### Large Files
- The python-docx library may have memory issues with very large documents
- Process in batches if needed

## Example Usage

Given a document with:
```
Some text here
[IMAGE: 1. GLP-1 RA/slide014t3m47.0s_ha7266061.jpg]
More text
```

After processing, the document will have:
```
Some text here
[Actual embedded image displayed here]
More text
```