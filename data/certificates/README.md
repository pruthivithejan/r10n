# Certificate Generator Automation

This folder contains the data files for the certificate generation automation.

## Files:

### `recipients.txt`
CSV format with recipient information:
```
Name,Course/Event,Date,Achievement/Grade
John Smith,Workshop on AI,2024-06-28,Excellent Performance
```

### `config.json`
Certificate generation configuration:
- **template_pdf**: Path to the blank certificate template
- **output_directory**: Where to save generated certificates
- **fields**: Positioning and styling for each field
  - **x, y**: Position coordinates on the PDF
  - **font_size**: Size of the text
  - **font_weight**: "normal" or "bold"
  - **color**: RGB color array [R, G, B] (0-255 or 0-1)
  - **alignment**: "left", "center", or "right"

### `templates/`
Place your blank certificate PDF template here. The template should have empty spaces where text will be filled.

### `output/`
Generated certificates will be saved here with recipient names.

## Setup:
1. Create or obtain a blank certificate PDF template
2. Place the template in `templates/` folder
3. Update `config.json` with correct coordinates for text placement
4. Add recipients to `recipients.txt`
5. Adjust font sizes and positioning as needed

## Coordinate System:
- Origin (0,0) is at bottom-left of the PDF
- X increases from left to right
- Y increases from bottom to top
- Use PDF viewers with coordinate display to find exact positions

## Usage:
```bash
python src/main.py fill_certificates
```

## Tips:
- Test with one recipient first to verify positioning
- Use a PDF editor to measure coordinates
- Common certificate dimensions: 792x612 (letter landscape) or 842x595 (A4 landscape)
