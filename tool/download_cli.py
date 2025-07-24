#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
歷史資料下載工具 - 命令列版本
提供簡化的命令列介面
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tool.gethistory import HistoryDataDownloader
import timenormalyize as tn

def show_help():
    """顯示說明"""
    print("""
🔧 台股歷史資料下載工具 - 命令列版本

使用方式:
  python download_cli.py recent [天數] [來源]     # 下載最近幾天
  python download_cli.py month [來源]             # 下載當月
  python download_cli.py range [開始] [結束] [來源] # 下載日期範圍
  python download_cli.py single [日期] [來源]      # 下載單一日期
  python download_cli.py help                      # 顯示說明

參數說明:
  來源: twse/tpex/both (預設: both)
  日期格式: 1140725 或 114/07/25 或 2025-07-25

範例:
  python download_cli.py recent 7 both           # 最近7天，兩個市場
  python download_cli.py month twse               # 本月TWSE資料
  python download_cli.py range 1140701 1140731   # 7月份資料
  python download_cli.py single 1140725 tpex     # 單日TPEX資料
    """)

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['help', '-h', '--help']:
        show_help()
        return
    
    downloader = HistoryDataDownloader()
    command = sys.argv[1].lower()
    
    try:
        if command == "recent":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            source = sys.argv[3] if len(sys.argv) > 3 else "both"
            print(f"📅 下載最近 {days} 天的 {source.upper()} 資料")
            downloader.download_recent_days(days, source)
            
        elif command == "month":
            source = sys.argv[2] if len(sys.argv) > 2 else "both"
            print(f"📅 下載當月 {source.upper()} 資料")
            downloader.download_current_month(source)
            
        elif command == "range":
            if len(sys.argv) < 4:
                print("❌ 請提供開始和結束日期")
                return
            start_date = sys.argv[2]
            end_date = sys.argv[3]
            source = sys.argv[4] if len(sys.argv) > 4 else "both"
            
            print(f"📅 下載 {start_date} ~ {end_date} 的 {source.upper()} 資料")
            downloader.download_date_range(start_date, end_date, source)
            
        elif command == "single":
            if len(sys.argv) < 3:
                print("❌ 請提供日期")
                return
            date = sys.argv[2]
            source = sys.argv[3] if len(sys.argv) > 3 else "both"
            
            print(f"📅 下載 {date} 的 {source.upper()} 資料")
            result = downloader.download_single_date(date, source)
            
            # 顯示詳細結果
            print(f"\n📊 下載結果:")
            print(f"   日期: {result['date']}")
            print(f"   TWSE: {'✅' if result['twse_success'] else '❌'} ({result['twse_count']} 檔)")
            print(f"   TPEX: {'✅' if result['tpex_success'] else '❌'} ({result['tpex_count']} 檔)")
            if result['errors']:
                print(f"   錯誤: {', '.join(result['errors'])}")
                
        else:
            print(f"❌ 未知命令: {command}")
            show_help()
            
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")
        show_help()

if __name__ == "__main__":
    main()
