#!/bin/bash

# Test CGM multi-slide merge
echo "Testing CGM multi-slide merge..."

# Set base directory with proper quotes
BASE_DIR="/Users/zino/Desktop/ADA2025/What's New with Continuous Glucose Monitoring"

# Run the merge
python merge_transcript_multi_slides.py \
    "${BASE_DIR}/transcription-21.txt" \
    "${BASE_DIR}/1. The Accuracy of a Novel CGM.md:${BASE_DIR}/1. The Accuracy of a Novel CGM" \
    "${BASE_DIR}/2. A Real-time Recalibration Algorithm To Improve The Accuracy Of CGM Sensors In Newborns.md:${BASE_DIR}/2. A Real-time Recalibration Algorithm To Improve The Accuracy Of CGM Sensors In Newborns" \
    --output cgm_test_merge