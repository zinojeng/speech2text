#!/bin/bash

base_dir="/Volumes/WD_BLACK/國際年會/ADA2025/Obesity/Incretin-Based Combination Therapies for Obesity—Clinical Studies/Incretin-Based Combination Therapies for Obesity—Clinical Studies"

echo "Testing folder detection..."
echo ""

for num in 1 2 3 4; do
    echo "=== Looking for folders starting with $num ==="
    
    # Method 1: Direct pattern
    echo "Method 1 - Direct ls:"
    ls -d "$base_dir"/${num}.* 2>/dev/null | while read dir; do
        if [ -d "$dir" ]; then
            echo "  Found: $(basename "$dir")"
        fi
    done
    
    echo ""
done