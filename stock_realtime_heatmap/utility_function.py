
def get_unique_stocks(my_category_data):
    """
    整理 my_category_data 不重複的股票資訊
    
    Returns:
        dict: 股票資訊字典，格式為 {
            'stock_id': {
                'name': '股票名稱',
                'categories': ['分類1', '分類2', ...]
            }
        }
    """
        
    # 使用字典來儲存不重複的股票資訊
    unique_stocks = {}
    
    # 檢查並收集所有股票
    if '台股' in my_category_data:
        for category_name, stocks in my_category_data['台股'].items():
            # 將每個分類下的股票資訊加入字典中
            for stock_id, stock_info in stocks.items():
                # 如果股票不存在，創建新的記錄
                if stock_id not in unique_stocks:
                    unique_stocks[stock_id] = {
                        'name': stock_info['股票'].strip(),  # 移除可能的空白
                        'categories': [category_name]
                    }
                # 如果股票已存在，只添加新的分類
                else:
                    if category_name not in unique_stocks[stock_id]['categories']:
                        unique_stocks[stock_id]['categories'].append(category_name)
    
    return unique_stocks

def get_section_category_momentum_data(search_path, num=10):
    
    """
    收集最近 n 天的 TPEX JSON 檔案路徑
    Args:
        num: 要收集的天數，預設10天 2 weeks
    Returns:
        list: 檔案路徑列表，由新到舊排序
    """
    
    from datetime import datetime, timedelta
    import os

    file_paths = []
    current_date = datetime.now()
    
    # 收集最近 n 天的檔案路徑
    days_checked = 0
    found_files = 0
    
    while found_files < num:
        check_date = current_date - timedelta(days=days_checked)
        # 轉換西元年為民國年 (yyyy -> yyy)
        year = check_date.year - 1911
        # 格式化檔名 (ex: 1140808.json)
        file_name = f"{year}{check_date.strftime('%m%d')}.json"
        file_path = os.path.join(search_path, file_name)
        
        if os.path.exists(file_path):
            file_paths.append(file_name)
            found_files += 1
            
        days_checked += 1
        
        # 避免無限迴圈，設定最大檢查天數
        if days_checked > 28:  # 設定一個合理的上限
            break

    return file_paths

def collect_stock_momentum(my_twse_path, my_tpex_path, date_files, unique_stocks_dict):
    """
    收集每個股票在特定日期的漲幅資訊
    
    Args:
        date_files (list): 日期檔案名稱列表 (例如: ['1140807.json', '1140806.json'])
        unique_stocks_dict (dict): 不重複股票的字典
        
    Returns:
        dict: 包含每個股票漲幅資訊和日期的字典，格式為:
        {
            'stock_id': {
                'name': '股票名稱',
                'categories': ['分類1', '分類2'],
                'momentum_list': [1.2, -0.5, ...]  # 依照日期順序的漲幅列表
            },
            'dates': ['1140807.json', ...]  # 日期檔案列表
        }
    """
    import json
    import os
    
    result_dict = {}
    
    # 初始化結果字典，保留原有資訊並添加漲幅列表
    for stock_id, stock_info in unique_stocks_dict.items():
        result_dict[stock_id] = {
            'name': stock_info['name'],
            'categories': stock_info['categories'],
            'momentum_list': []  # 用來存放歷史漲幅
        }
    
    # 加入日期檔案列表
    result_dict['dates'] = date_files
    
    # 處理每個日期檔案
    for date_file in date_files:
        # 先嘗試從 TWSE 讀取
        twse_path = os.path.join(my_twse_path, date_file)
        tpex_path = os.path.join(my_tpex_path, date_file)
        
        # 讀取 TWSE 資料
        twse_data = {}
        if os.path.exists(twse_path):
            with open(twse_path, 'r', encoding='utf-8') as f:
                twse_data = json.load(f)
        
        # 讀取 TPEX 資料
        tpex_data = {}
        if os.path.exists(tpex_path):
            with open(tpex_path, 'r', encoding='utf-8') as f:
                tpex_data = json.load(f)
        
        # 對每個股票找尋當日漲幅
        for stock_id in unique_stocks_dict.keys():
            momentum = None
            
            # 先找 TWSE
            if 'data' in twse_data and stock_id in twse_data['data']:
                stock_data = twse_data['data'][stock_id]
                if len(stock_data) > 0:
                    momentum = float(stock_data[-1])  # 取"最後一個元素(注意變更)"作為漲幅
            
            # 如果在 TWSE 找不到，找 TPEX
            if momentum is None and 'data' in tpex_data and stock_id in tpex_data['data']:
                stock_data = tpex_data['data'][stock_id]
                if len(stock_data) > 0:
                    momentum = float(stock_data[-1])  # 取"最後一個元素(注意變更)"作為漲幅
            
            # 將漲幅加入結果，如果都找不到就用 0.0
            result_dict[stock_id]['momentum_list'].append(momentum if momentum is not None else 0.0)
    
    return result_dict

def calculate_category_momentum(my_category_data, momentum_data):
    """
    計算每個類別的平均漲幅
    
    Args:
        my_category_data (dict): my_stock_category.json 的內容
        momentum_data (dict): collect_stock_momentum 函式的輸出結果
        
    Returns:
        dict: 各類別的平均漲幅資料，格式為:
        {
            '類別名稱': {
                'stocks': ['2330', '2317', ...],  # 該類別包含的股票
                'avg_momentum': [1.2, -0.5, ...], # 該類別每天的平均漲幅
                'stock_count': 3                   # 該類別包含的股票數量
            }
        }
    """
    result = {}
    dates = momentum_data.get('dates', [])
    date_count = len(dates)
    
    # 檢查台股分類
    if '台股' not in my_category_data:
        return result
        
    # 處理每個類別
    for category_name, stocks in my_category_data['台股'].items():
        # 初始化該類別的資料
        result[category_name] = {
            'stocks': list(stocks.keys()),
            'avg_momentum': [0.0] * date_count,  # 初始化為0
            'stock_count': len(stocks)
        }
        
        # 計算每天的平均漲幅
        for date_idx in range(date_count):
            momentum_sum = 0.0
            valid_stock_count = 0
            
            # 加總該類別所有股票的漲幅
            for stock_id in stocks.keys():
                if stock_id in momentum_data:
                    momentum = momentum_data[stock_id]['momentum_list'][date_idx]
                    if momentum is not None:  # 如果有有效的漲幅數據
                        momentum_sum += momentum
                        valid_stock_count += 1
            
            # 計算平均值
            if valid_stock_count > 0:
                result[category_name]['avg_momentum'][date_idx] = momentum_sum / valid_stock_count
            else:
                result[category_name]['avg_momentum'][date_idx] = 0.0
                
    return result

