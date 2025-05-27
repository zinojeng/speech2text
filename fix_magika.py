#!/usr/bin/env python3
"""
修復 magika 套件的 JSON 配置檔案問題
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_magika_issue():
    """修復 magika 套件的問題"""
    try:
        logger.info("開始修復 magika 套件問題...")
        
        # 方法 1: 重新安裝 magika
        logger.info("步驟 1: 卸載現有的 magika 套件...")
        subprocess.run([
            sys.executable, "-m", "pip", "uninstall", "magika", "-y"
        ], check=True)
        
        logger.info("步驟 2: 清理 pip 快取...")
        subprocess.run([
            sys.executable, "-m", "pip", "cache", "purge"
        ], check=False)  # 不強制成功，因為某些環境可能不支援
        
        logger.info("步驟 3: 重新安裝 magika 套件...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "magika", "--no-cache-dir"
        ], check=True)
        
        logger.info("magika 套件修復完成！")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"修復過程中發生錯誤: {e}")
        return False
    except Exception as e:
        logger.error(f"未預期的錯誤: {e}")
        return False


def test_magika():
    """測試 magika 是否正常工作"""
    try:
        import magika
        magika.Magika()  # 測試是否能正常初始化
        logger.info("magika 套件測試成功！")
        return True
    except Exception as e:
        logger.error(f"magika 測試失敗: {e}")
        return False


if __name__ == "__main__":
    print("=== MarkItDown magika 套件修復工具 ===")
    
    # 首先測試當前狀態
    print("\n1. 測試當前 magika 狀態...")
    if test_magika():
        print("✅ magika 套件運作正常，無需修復")
        sys.exit(0)
    
    # 嘗試修復
    print("\n2. 開始修復 magika 套件...")
    if fix_magika_issue():
        print("\n3. 重新測試 magika...")
        if test_magika():
            print("✅ 修復成功！magika 套件現在可以正常使用")
        else:
            print("❌ 修復後測試仍然失敗")
            sys.exit(1)
    else:
        print("❌ 修復失敗")
        sys.exit(1) 