#!/usr/bin/env python
import os
import sys
import subprocess
import shutil
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """修復 magika 套件問題的主要函數"""
    logger.info("開始修復 magika 套件...")
    
    try:
        # 卸載 magika
        logger.info("卸載 magika 套件...")
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "magika", "-y"], check=True)
        
        # 清理 pip 緩存
        logger.info("清理 pip 緩存...")
        subprocess.run([sys.executable, "-m", "pip", "cache", "purge"], check=True)
        
        # 重新安裝 magika
        logger.info("重新安裝 magika 套件...")
        subprocess.run([sys.executable, "-m", "pip", "install", "magika", "--no-cache-dir"], check=True)
        
        logger.info("修復完成！magika 套件已重新安裝")
        print("\n✅ magika 套件修復成功！\n")
    except Exception as e:
        logger.error(f"修復過程中發生錯誤: {str(e)}")
        print(f"\n❌ 修復失敗: {str(e)}\n")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 