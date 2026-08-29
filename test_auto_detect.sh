#!/bin/bash

# 測試自動偵測功能的腳本
# 創建測試資料夾結構

TEST_DIR="/tmp/test_slides_auto_detect"
echo "創建測試資料夾結構於：$TEST_DIR"

# 清理舊的測試資料夾
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"

# 創建編號資料夾結構
for i in {1..3}; do
    # 創建編號資料夾
    mkdir -p "$TEST_DIR/$i"
    
    # 創建測試 .md 檔案
    echo "# Slide $i Content" > "$TEST_DIR/$i/slide$i.md"
    echo "This is the content for slide $i" >> "$TEST_DIR/$i/slide$i.md"
    
    # 創建圖片資料夾並放入測試圖片
    mkdir -p "$TEST_DIR/$i/images"
    touch "$TEST_DIR/$i/images/slide_00${i}_t${i}m0s.jpg"
    touch "$TEST_DIR/$i/images/slide_00${i}_t${i}m30s.jpg"
done

# 創建另一種編號格式
mkdir -p "$TEST_DIR/4."
echo "# Slide 4 Content" > "$TEST_DIR/4./presentation4.md"
mkdir -p "$TEST_DIR/4./img"
touch "$TEST_DIR/4./img/image1.png"

# 創建直接的 .md 檔案（沒有資料夾）
echo "# Slide 5 Content" > "$TEST_DIR/5_slide.md"

# 顯示創建的結構
echo ""
echo "已創建的測試結構："
tree "$TEST_DIR" 2>/dev/null || find "$TEST_DIR" -type f | sort

echo ""
echo "測試資料夾準備完成！"
echo "請使用以下路徑進行測試："
echo "$TEST_DIR"