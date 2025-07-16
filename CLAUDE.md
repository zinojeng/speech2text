# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment

### Quick Start
```bash
# Start the main Streamlit application
./start_app.sh

# For batch audio processing
./audio_auto.sh [folder_path] [model] [format] [--combined]

# Examples:
# Individual SRT files per audio file
./audio_auto.sh /path/to/audio/folder gpt-4o-mini-transcribe srt

# Combined SRT with continuous timestamps
./audio_auto.sh /path/to/audio/folder gpt-4o-mini-transcribe srt --combined
```

### Virtual Environment Setup
The repository uses multiple virtual environments:
- `venv_app/` - Main application environment
- `venv/` - Development environment
- `venv_markitdown/` - MarkItDown specific dependencies

### API Configuration
Create `.env` file with required API keys:
```bash
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key
# Optional:
# ELEVENLABS_API_KEY=your_elevenlabs_key
```

## Core Architecture

### Speech-to-Text Pipeline
The system supports multiple STT backends with automatic fallback:

1. **GPT-4o Models** (`gpt4o_transcribe.py`)
   - `gpt-4o-transcribe` - Higher quality, more expensive
   - `gpt-4o-mini-transcribe` - More economical, default choice
   - Supports automatic file splitting for large audio files

2. **Whisper Integration** (`whisper_stt.py`)
   - Local processing option
   - Multiple model sizes available
   - Fallback when API quotas are exceeded

3. **ElevenLabs STT** (`elevenlabs_stt.py`)
   - Premium transcription service
   - Speaker diarization support
   - File size limitations (25MB, 8min for diarization)

### Document Processing System
- **MarkItDown Integration** (`markitdown_utils.py`) - Universal document converter
- **Image Analysis** (`image_analyzer.py`) - Vision API for image-rich documents
- **Alternative Converters** (`alternative_pptx_converter.py`) - Specialized PPTX handling

### Batch Processing Workflow
```bash
# Automatic model selection and file splitting
python batch_audio_processor.py folder_path [model]

# With shell script wrapper (recommended)
./audio_auto.sh [folder_path] [model] [format] [--combined]

# Combined output examples:
./audio_auto.sh /audio/folder gpt-4o-mini-transcribe srt --combined
./audio_auto.sh /audio/folder gpt-4o-mini-transcribe markdown --combined
```

Key features:
- Recursive folder scanning for audio/text files
- Automatic file splitting (25MB limit, 5-minute segments)
- Agenda file matching (same-name text files)
- Word document output generation
- **NEW: Combined output mode** - merges all transcripts into single file
  - SRT format: Continuous timestamps across all files
  - Text/Markdown: File headers with content separation

## Essential Commands

### Application Startup
```bash
# Main Streamlit interface
./start_app.sh

# Multi-file batch processor with UI
streamlit run multi_file_processor.py

# Alternative Gradio interface  
source venv_app/bin/activate && python app.py

# Command-line batch processing automation
./audio_auto.sh
```

### Individual File Processing
```bash
# Direct transcription with GPT-4o
python gpt4o_transcribe.py audio.mp3 --model gpt-4o-mini-transcribe

# Document conversion
python -c "from markitdown_utils import convert_file_to_markdown; print(convert_file_to_markdown('file.pdf'))"
```

### Troubleshooting
```bash
# Fix MarkItDown magika issues
python fix_magika.py

# Check audio file constraints
python -c "from utils import check_file_constraints; print(check_file_constraints('audio.mp3'))"
```

## Key Implementation Details

### File Processing Utils (`utils.py`)
- `split_large_audio()` - Automatic audio segmentation
- `check_file_size()` - Size validation (25MB limit)
- Token counting and cost estimation for LLM operations

### Modular STT Architecture
Each STT backend implements standard interface:
- `transcribe_audio_[backend]()` functions
- Consistent error handling and logging
- Automatic fallback mechanisms

### Multi-Interface Support
- **main_app.py** - Primary Streamlit interface with full features
- **multi_file_processor.py** - Streamlit UI for batch processing multiple files
  - Folder/subfolder scanning for audio files
  - Multiple file upload support
  - Parallel processing with progress tracking
  - Combined or individual export options
  - Integrated Word document generation
- **app.py** - Gradio interface for alternative deployment
- **batch_audio_processor.py** - Command-line batch processing

### Auto-Splitting Logic
Large files are automatically split into:
- 5-minute segments for transcription
- Temporary files cleaned after processing
- Progressive transcription with API rate limiting

## Deployment Notes

### Safari Connection Issues
Use `http://127.0.0.1:8501` instead of `localhost` for Safari compatibility.

### Streamlit Server Configuration
```bash
streamlit run main_app.py --server.address 0.0.0.0 --server.port 8501
```

### Dependencies Management
- Core dependencies in `requirements.txt`
- MarkItDown specific packages may need separate installation
- ffmpeg required for audio processing

## Model Selection Strategy

Default model hierarchy:
1. `gpt-4o-mini-transcribe` (cost-effective, good quality)
2. `gpt-4o-transcribe` (premium quality)
3. Local Whisper (quota exhaustion fallback)
4. ElevenLabs (premium features like diarization)

Cost considerations built into `utils.py` with token counting and price estimation per model.

## Troubleshooting

### Multi-Slide Image Display Issues

When processing multiple slides with their respective image folders, images may not display properly. This has been fixed in `merge_transcript_multi_slides.py`:

**Previous Issue**: Images from different slides with the same timestamp would overwrite each other, causing only the last slide's images to be available.

**Solution Implemented**:
1. Changed image storage structure from `{time: img_path}` to `{time: [(slide_index, img_path), ...]}`
2. Removed the confusing 10000-second offset mechanism
3. Images are now stored with their actual timestamps and slide associations
4. When multiple slides have images at the same timestamp, the system selects the image from the earliest slide

**Usage for Multiple Slides with Images**:
```bash
# Interactive mode (recommended)
./interactive_merge.sh

# Command line
python merge_transcript_multi_slides.py transcript.txt \
  "slide1.md:images1/" \
  "slide2.md:images2/" \
  "slide3.md:images3/" \
  --output merged_output
```

**Debugging Image Issues**:
- Check logs for "載入了 X 張圖片" messages for each slide
- Verify image filenames follow the pattern: `slide_XXX_tXmYs.jpg`
- Ensure image folders are correctly specified with colon separator
- Look for "插入圖片" log entries to confirm successful insertion