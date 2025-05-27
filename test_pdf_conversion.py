#!/usr/bin/env python3
"""
測試 PDF 轉 Markdown 功能
"""

import os
import tempfile
from markitdown_utils import convert_file_to_markdown


def create_test_text_file():
    """創建一個測試用的文字檔案"""
    content = """# 測試文件

這是一個測試文件，用來驗證 MarkItDown 功能是否正常運作。

## 功能特色

- 支援多種檔案格式
- 轉換為 Markdown 格式
- 保持文件結構

## 結論

如果您看到這個內容，表示轉換功能正常運作！
"""
    
    # 創建臨時檔案
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(content)
        return f.name


def test_conversion():
    """測試檔案轉換功能"""
    print("=== MarkItDown 轉換功能測試 ===\n")
    
    # 創建測試檔案
    test_file = create_test_text_file()
    print(f"1. 創建測試檔案: {test_file}")
    
    try:
        # 測試轉換
        print("2. 開始轉換...")
        success, markdown_text, info = convert_file_to_markdown(
            input_path=test_file,
            use_llm=False
        )
        
        if success:
            print("✅ 轉換成功！")
            print(f"   檔案大小: {info.get('file_size', 'N/A')} bytes")
            print(f"   內容長度: {info.get('content_length', 'N/A')} 字元")
            print("\n--- 轉換結果 ---")
            print(markdown_text[:500] + "..." if len(markdown_text) > 500 else markdown_text)
        else:
            print("❌ 轉換失敗")
            print(f"   錯誤: {info.get('error', '未知錯誤')}")
            
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
    
    finally:
        # 清理測試檔案
        try:
            os.remove(test_file)
            print(f"\n3. 已清理測試檔案: {test_file}")
        except Exception as e:
            print(f"清理檔案時發生錯誤: {e}")


if __name__ == "__main__":
    test_conversion() 