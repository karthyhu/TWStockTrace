#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
歷史股票資料下載工具
支援 TWSE (台灣證券交易所) 和 TPEX (櫃買中心) 資料
可指定日期範圍批量下載
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import timenormalyize as tn
from TWSE_manager import TWSE_manager
from TPEX_manager import TPEX_manager


class HistoryDataDownloader:
    def __init__(self, twse_dir='./raw_stock_data/daily/twse', tpex_dir='./raw_stock_data/daily/tpex'):
        """
        初始化歷史資料下載器
        
        Args:
            twse_dir: TWSE 資料儲存目錄
            tpex_dir: TPEX 資料儲存目錄
        """
        self.twse_manager = TWSE_manager(twse_dir)
        self.tpex_manager = TPEX_manager(tpex_dir)
        self.downloaded_dates = set()
        self.failed_dates = set()
        
    def generate_date_range(self, start_date: str, end_date: str, exclude_weekends: bool = True):
        """
        生成日期範圍列表
        
        Args:
            start_date: 開始日期 (支援各種格式)
            end_date: 結束日期 (支援各種格式)
            exclude_weekends: 是否排除週末
            
        Returns:
            日期列表 (民國年格式)
        """
        # 統一轉換為西元年日期進行計算
        start_ce = tn.normalize_date(start_date, "CE", "")
        end_ce = tn.normalize_date(end_date, "CE", "")
        
        # 轉換為 datetime 物件
        start_dt = datetime.datetime.strptime(start_ce, "%Y%m%d")
        end_dt = datetime.datetime.strptime(end_ce, "%Y%m%d")
        
        date_list = []
        current_dt = start_dt
        
        while current_dt <= end_dt:
            # 排除週末 (週六=5, 週日=6)
            if not exclude_weekends or current_dt.weekday() < 5:
                # 轉換回民國年格式
                ce_date = current_dt.strftime("%Y%m%d")
                roc_date = tn.normalize_date(ce_date, "ROC", "")
                date_list.append(roc_date)
            
            current_dt += datetime.timedelta(days=1)
        
        return date_list
    
    def download_single_date(self, date: str, source: str = "both", delay_range: tuple = (0.5, 2.0)):
        """
        下載單一日期的資料
        
        Args:
            date: 日期字串
            source: 資料來源 ("twse", "tpex", "both")
            delay_range: 請求延遲範圍 (秒)
            
        Returns:
            下載結果字典
        """
        result = {
            'date': date,
            'twse_success': False,
            'tpex_success': False,
            'twse_count': 0,
            'tpex_count': 0,
            'errors': []
        }
        
        # 隨機延遲避免過頻請求
        if delay_range:
            time.sleep(random.uniform(delay_range[0], delay_range[1]))
        
        # 下載 TWSE 資料
        if source in ["twse", "both"]:
            try:
                print(f"📊 下載 TWSE {date}...", end=" ")
                twse_data = self.twse_manager.download_internalurl(date)
                if twse_data and twse_data.get('data'):
                    result['twse_success'] = True
                    result['twse_count'] = len(twse_data['data'])
                    print(f"✅ ({result['twse_count']} 檔)")
                else:
                    print("❌ 無資料")
                    result['errors'].append(f"TWSE {date}: 無資料")
            except Exception as e:
                print(f"❌ 錯誤: {e}")
                result['errors'].append(f"TWSE {date}: {e}")
        
        # 下載 TPEX 資料
        if source in ["tpex", "both"]:
            try:
                print(f"📈 下載 TPEX {date}...", end=" ")
                tpex_data = self.tpex_manager.download_get_once(date)
                if tpex_data and tpex_data.get('data'):
                    result['tpex_success'] = True
                    result['tpex_count'] = len(tpex_data['data'])
                    print(f"✅ ({result['tpex_count']} 檔)")
                else:
                    print("❌ 無資料")
                    result['errors'].append(f"TPEX {date}: 無資料")
            except Exception as e:
                print(f"❌ 錯誤: {e}")
                result['errors'].append(f"TPEX {date}: {e}")
        
        return result
    
    def download_date_range(self, start_date: str, end_date: str, source: str = "both", 
                          exclude_weekends: bool = True, max_workers: int = 1, 
                          delay_range: tuple = (1.0, 3.0)):
        """
        下載日期範圍的資料
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            source: 資料來源 ("twse", "tpex", "both")
            exclude_weekends: 是否排除週末
            max_workers: 最大併發數 (建議設為1避免被封鎖)
            delay_range: 請求延遲範圍
            
        Returns:
            下載統計結果
        """
        print(f"🚀 開始下載歷史資料...")
        print(f"📅 日期範圍: {start_date} ~ {end_date}")
        print(f"📊 資料來源: {source.upper()}")
        print(f"🔧 併發數: {max_workers}")
        print("=" * 60)
        
        # 生成日期列表
        date_list = self.generate_date_range(start_date, end_date, exclude_weekends)
        total_dates = len(date_list)
        
        print(f"📋 共需下載 {total_dates} 個交易日")
        if exclude_weekends:
            print("📝 已排除週末")
        print("=" * 60)
        
        # 統計變數
        results = []
        start_time = time.time()
        
        if max_workers == 1:
            # 單線程順序下載 (推薦)
            for i, date in enumerate(date_list, 1):
                print(f"\n📈 進度: {i}/{total_dates} ({i/total_dates*100:.1f}%)")
                result = self.download_single_date(date, source, delay_range)
                results.append(result)
                
                # 統計更新
                if result['twse_success'] or result['tpex_success']:
                    self.downloaded_dates.add(date)
                else:
                    self.failed_dates.add(date)
        else:
            # 多線程下載 (小心使用)
            print("⚠️  使用多線程下載，請注意避免被伺服器封鎖")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任務
                future_to_date = {
                    executor.submit(self.download_single_date, date, source, delay_range): date 
                    for date in date_list
                }
                
                # 收集結果
                for i, future in enumerate(as_completed(future_to_date), 1):
                    date = future_to_date[future]
                    print(f"\n📈 進度: {i}/{total_dates} ({i/total_dates*100:.1f}%)")
                    
                    try:
                        result = future.result()
                        results.append(result)
                        
                        if result['twse_success'] or result['tpex_success']:
                            self.downloaded_dates.add(date)
                        else:
                            self.failed_dates.add(date)
                    except Exception as e:
                        print(f"❌ 日期 {date} 下載失敗: {e}")
                        self.failed_dates.add(date)
        
        # 統計結果
        elapsed_time = time.time() - start_time
        self._print_summary(results, elapsed_time)
        
        return results
    
    def _print_summary(self, results, elapsed_time):
        """列印下載摘要"""
        print("\n" + "=" * 60)
        print("📊 下載完成摘要")
        print("=" * 60)
        
        total_dates = len(results)
        twse_success = sum(1 for r in results if r['twse_success'])
        tpex_success = sum(1 for r in results if r['tpex_success'])
        total_twse_stocks = sum(r['twse_count'] for r in results)
        total_tpex_stocks = sum(r['tpex_count'] for r in results)
        
        print(f"📅 處理日期數: {total_dates}")
        print(f"📊 TWSE 成功: {twse_success} 天 ({total_twse_stocks} 檔股票)")
        print(f"📈 TPEX 成功: {tpex_success} 天 ({total_tpex_stocks} 檔股票)")
        print(f"⏱️  總耗時: {elapsed_time:.1f} 秒")
        print(f"⚡ 平均每日: {elapsed_time/total_dates:.1f} 秒")
        
        # 顯示失敗的日期
        failed_results = [r for r in results if not r['twse_success'] and not r['tpex_success']]
        if failed_results:
            print(f"\n❌ 完全失敗的日期 ({len(failed_results)} 天):")
            for result in failed_results[:10]:  # 只顯示前10個
                print(f"   {result['date']}")
            if len(failed_results) > 10:
                print(f"   ... 還有 {len(failed_results)-10} 天")
        
        # 顯示部分失敗
        partial_failed = [r for r in results if (r['twse_success'] or r['tpex_success']) and r['errors']]
        if partial_failed:
            print(f"\n⚠️  部分失敗的日期 ({len(partial_failed)} 天):")
            for result in partial_failed[:5]:
                print(f"   {result['date']}: {', '.join(result['errors'][:2])}")
    
    def download_recent_days(self, days: int = 7, source: str = "both"):
        """
        下載最近幾天的資料
        
        Args:
            days: 天數
            source: 資料來源
        """
        # 計算日期範圍
        end_date = tn.get_current_date("ROC", "")
        start_dt = datetime.datetime.now() - datetime.timedelta(days=days-1)
        start_date = tn.normalize_date(start_dt.strftime("%Y%m%d"), "ROC", "")
        
        print(f"📅 下載最近 {days} 天的資料")
        return self.download_date_range(start_date, end_date, source)
    
    def download_current_month(self, source: str = "both"):
        """下載當月資料"""
        now = datetime.datetime.now()
        start_date = now.replace(day=1).strftime("%Y%m%d")
        end_date = tn.get_current_date("CE", "")
        
        start_roc = tn.normalize_date(start_date, "ROC", "")
        end_roc = tn.normalize_date(end_date, "ROC", "")
        
        print("📅 下載當月資料")
        return self.download_date_range(start_roc, end_roc, source)


def main():
    """主程式"""
    print("🔧 台股歷史資料下載工具")
    print("=" * 40)
    
    downloader = HistoryDataDownloader()
    
    # 範例使用
    if len(sys.argv) > 1:
        if sys.argv[1] == "recent":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            downloader.download_recent_days(days)
        elif sys.argv[1] == "month":
            downloader.download_current_month()
        elif sys.argv[1] == "range" and len(sys.argv) >= 4:
            start_date = sys.argv[2]
            end_date = sys.argv[3]
            source = sys.argv[4] if len(sys.argv) > 4 else "both"
            downloader.download_date_range(start_date, end_date, source)
        else:
            print("使用方式:")
            print("python gethistory.py recent [天數]")
            print("python gethistory.py month")
            print("python gethistory.py range [開始日期] [結束日期] [來源]")
    else:
        # 互動式選單
        show_interactive_menu(downloader)


def show_interactive_menu(downloader):
    """顯示互動式選單"""
    while True:
        print("\n🔧 台股歷史資料下載工具")
        print("=" * 40)
        print("1. 下載最近幾天資料")
        print("2. 下載當月資料")
        print("3. 下載指定日期範圍")
        print("4. 下載單一日期")
        print("0. 離開")
        print("=" * 40)
        
        choice = input("請選擇功能 (0-4): ").strip()
        
        if choice == "0":
            print("👋 再見！")
            break
        elif choice == "1":
            days = input("請輸入天數 (預設7): ").strip()
            days = int(days) if days.isdigit() else 7
            source = input("資料來源 (twse/tpex/both, 預設both): ").strip() or "both"
            downloader.download_recent_days(days, source)
        elif choice == "2":
            source = input("資料來源 (twse/tpex/both, 預設both): ").strip() or "both"
            downloader.download_current_month(source)
        elif choice == "3":
            start_date = input("開始日期 (如: 1140701 或 114/07/01): ").strip()
            end_date = input("結束日期 (如: 1140731 或 114/07/31): ").strip()
            source = input("資料來源 (twse/tpex/both, 預設both): ").strip() or "both"
            
            if start_date and end_date:
                downloader.download_date_range(start_date, end_date, source)
            else:
                print("❌ 請輸入有效的日期範圍")
        elif choice == "4":
            date = input("請輸入日期 (如: 1140725 或 114/07/25): ").strip()
            source = input("資料來源 (twse/tpex/both, 預設both): ").strip() or "both"
            
            if date:
                result = downloader.download_single_date(date, source)
                print(f"\n📊 下載結果: {result}")
            else:
                print("❌ 請輸入有效的日期")
        else:
            print("❌ 無效選擇，請重新輸入")


if __name__ == "__main__":
    main()
