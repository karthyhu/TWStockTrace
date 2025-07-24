#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
歷史資料下載工具使用範例
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tool.gethistory import HistoryDataDownloader

def example_usage():
    """使用範例"""
    print("🔧 歷史資料下載工具使用範例")
    print("=" * 50)
    
    # 建立下載器
    downloader = HistoryDataDownloader()
    
    # 範例1: 下載最近3天的資料
    print("\n📋 範例1: 下載最近3天的資料")
    print("-" * 30)
    # downloader.download_recent_days(3, "both")
    
    # 範例2: 下載指定日期範圍 (只下載TWSE)
    print("\n📋 範例2: 下載指定日期範圍")
    print("-" * 30)
    downloader.download_date_range(
        start_date="1140722",   # 民國114年7月22日
        end_date="1140724",     # 民國114年7月24日
        source="twse",          # 只下載TWSE
        exclude_weekends=True,  # 排除週末
        max_workers=1,          # 單線程
        delay_range=(1.0, 2.0)  # 延遲1-2秒
    )
    
    # 範例3: 下載單一日期
    print("\n📋 範例3: 下載單一日期")
    print("-" * 30)
    # result = downloader.download_single_date("1140725", "both")
    # print(f"下載結果: {result}")

def quick_test():
    """快速測試"""
    print("🧪 快速測試")
    print("=" * 30)
    
    downloader = HistoryDataDownloader()
    
    # 測試日期範圍生成
    print("📅 測試日期範圍生成:")
    dates = downloader.generate_date_range("1140722", "1140726", exclude_weekends=True)
    print(f"日期列表: {dates}")
    
    # 測試單一日期下載
    print("\n📊 測試單一日期下載:")
    result = downloader.download_single_date("1140724", "twse", delay_range=None)
    print(f"下載結果: {result}")

if __name__ == "__main__":
    # 選擇要執行的範例
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        quick_test()
    else:
        example_usage()
