import datetime
import re
import pytz


def normalize_date(date: str, output_format: str = "ROC", separator: str = "") -> str:
    """
    將日期字串轉換為統一格式

    Args:
        date: 輸入日期字串，支援西元年或民國年，可包含分隔符號
        output_format: 輸出格式 "CE" (西元) 或 "ROC" (民國)
        separator: 連接符號，預設為空字串，可選 "-", "/", "" 等

    Returns:
        格式化後的日期字串，月份和日期固定為兩位數

    Examples:
        normalize_date("1140721") -> "20250721"
        normalize_date("114/7/21", "CE", "-") -> "2025-07-21"
        normalize_date("2025-7-21", "ROC") -> "1140721"
    """
    if not date:
        return ""

    # 先檢查是否包含分隔符號，如果有則分別處理
    date_str = str(date).strip()

    # 檢查是否包含分隔符號
    if "/" in date_str or "-" in date_str:
        # 使用分隔符號分割日期
        parts = re.split(r"[/-]", date_str)
        if len(parts) != 3:
            raise ValueError(f"日期格式不正確: {date}")

        year_str, month_str, day_str = parts

        # 判斷年份格式
        year_len = len(year_str)
        if year_len == 4:  # 西元年
            is_roc = False
        elif year_len == 3:  # 民國年
            is_roc = True
        elif year_len == 2:  # 兩位數年份，需要判斷
            year_num = int(year_str)
            if year_num > 50:
                is_roc = False  # 19XX年
                year_str = "19" + year_str
            else:
                is_roc = False  # 20XX年
                year_str = "20" + year_str
        elif year_len == 1:  # 一位數年份，假設為民國年
            is_roc = True
            year_str = "00" + year_str
        else:
            raise ValueError(f"無法識別的年份格式: {year_str}")
    else:
        # 移除所有分隔符號
        clean_date = re.sub(r"[/-]", "", date_str)

        # 確保輸入是數字
        if not clean_date.isdigit():
            raise ValueError(f"日期格式不正確: {date}")

        # 解析日期字串
        if len(clean_date) == 7:  # YYYMMDD 格式 (民國年3位數)
            year_str = clean_date[:3]
            month_str = clean_date[3:5]
            day_str = clean_date[5:7]
            is_roc = True
        elif len(clean_date) == 8:  # YYYYMMDD 格式 (西元年4位數)
            year_str = clean_date[:4]
            month_str = clean_date[4:6]
            day_str = clean_date[6:8]
            is_roc = False
        elif len(clean_date) == 6:  # YYMMDD 格式，需要判斷是西元還是民國
            year_str = clean_date[:2]
            month_str = clean_date[2:4]
            day_str = clean_date[4:6]
            # 根據年份數字判斷
            year_num = int(year_str)
            if year_num >= 12:  # 民國12年(1923)以後，假設為西元19XX或20XX年
                if year_num > 50:
                    is_roc = False  # 19XX年
                    year_str = "19" + year_str
                else:
                    is_roc = False  # 20XX年
                    year_str = "20" + year_str
            else:  # 01-11，假設為民國1-11年或101-111年
                if year_num >= 1:
                    is_roc = True  # 民國年
                    year_str = "0" + year_str  # 補齊為民國0XX年
                else:
                    is_roc = False  # 2000年
                    year_str = "20" + year_str
        elif len(clean_date) == 5:  # YMMDD 格式 (民國年1位數)
            year_str = clean_date[:1]
            month_str = clean_date[1:3]
            day_str = clean_date[3:5]
            is_roc = True
            year_str = "00" + year_str  # 補齊為民國00X年
        else:
            raise ValueError(f"無法識別的日期格式: {date}")

    # 轉換為整數以便處理
    year = int(year_str)
    month = int(month_str)
    day = int(day_str)

    # 驗證月份和日期範圍
    if month < 1 or month > 12:
        raise ValueError(f"月份超出範圍 (1-12): {month}")
    if day < 1 or day > 31:
        raise ValueError(f"日期超出範圍 (1-31): {day}")

    # 轉換年份格式
    if output_format.upper() == "CE":
        # 輸出西元年
        if is_roc:
            ce_year = year + 1911  # 民國年轉西元年
        else:
            ce_year = year
        formatted_year = f"{ce_year:04d}"
    elif output_format.upper() == "ROC":
        # 輸出民國年
        if is_roc:
            roc_year = year
        else:
            roc_year = year - 1911  # 西元年轉民國年
            if roc_year < 1:
                raise ValueError(f"西元年 {year} 無法轉換為民國年")
        formatted_year = f"{roc_year:03d}"
    else:
        raise ValueError(f"不支援的輸出格式: {output_format}")

    # 格式化月份和日期為兩位數
    formatted_month = f"{month:02d}"
    formatted_day = f"{day:02d}"

    # 組合結果
    if separator:
        return f"{formatted_year}{separator}{formatted_month}{separator}{formatted_day}"
    else:
        return f"{formatted_year}{formatted_month}{formatted_day}"


def batch_normalize_dates(
    dates: list, output_format: str = "CE", separator: str = ""
) -> list:
    """
    批量處理日期格式化

    Args:
        dates: 日期字串列表
        output_format: 輸出格式 "CE" (西元) 或 "ROC" (民國)
        separator: 連接符號

    Returns:
        格式化後的日期字串列表
    """
    result = []
    for date in dates:
        try:
            normalized = normalize_date(date, output_format, separator)
            result.append(normalized)
        except Exception as e:
            print(f"處理日期 '{date}' 時發生錯誤: {e}")
            result.append(None)
    return result


def get_current_date(output_format: str = "CE", separator: str = "") -> str:
    """
    取得當前台灣時間的格式化日期字串

    Args:
        output_format: 輸出格式 "CE" (西元) 或 "ROC" (民國)
        separator: 連接符號

    Returns:
        格式化後的當前台灣時間日期字串
    """
    # 使用 pytz 獲取台灣時區
    taiwan_tz = pytz.timezone("Asia/Taipei")

    # 獲取台灣當前時間
    taiwan_now = datetime.datetime.now(taiwan_tz)
    today_str = taiwan_now.strftime("%Y%m%d")

    return normalize_date(today_str, output_format, separator)


def cal_date(start_date:str, offset_days:int) -> str:
    """
    計算新的日期，並確保回傳的日期為工作日（週一至週五）

    Args:
        start_date: 起始日期字串，格式可為 "YYYY-MM-DD"、"YYYYMMDD" 或民國年格式
        offset_days: 偏移工作天數（可以是正數或負數）

    Returns:
        計算後的工作日日期字串，格式與輸入格式相同
    """
    # 判斷輸入日期格式
    input_format = ""
    separator = ""
    is_roc = False
    
    # 檢查分隔符號
    if "-" in start_date:
        separator = "-"
    elif "/" in start_date:
        separator = "/"
    
    # 標準化日期格式為西元年 YYYY-MM-DD
    if separator:
        # 有分隔符號，判斷是否為民國年
        parts = start_date.split(separator)
        if len(parts[0]) == 3:  # 民國年 YYY-MM-DD
            is_roc = True
            normalized_date = normalize_date(start_date, "CE", "-")
        else:
            normalized_date = start_date if separator == "-" else normalize_date(start_date, "CE", "-")
    else:
        # 無分隔符號
        if len(start_date) == 7:  # YYYMMDD 民國年
            is_roc = True
            normalized_date = normalize_date(start_date, "CE", "-")
        else:
            normalized_date = normalize_date(start_date, "CE", "-")
    
    # 記錄原始格式
    orig_format = "ROC" if is_roc else "CE"
    orig_separator = separator
    
    # 解析標準化後的日期
    start_dt = datetime.datetime.strptime(normalized_date, "%Y-%m-%d")
    
    # 計算工作日偏移
    days_moved = 0
    day_increment = 1 if offset_days >= 0 else -1
    current_dt = start_dt
    
    # 處理工作日偏移
    while abs(days_moved) < abs(offset_days):
        current_dt += datetime.timedelta(days=day_increment)
        # 檢查是否為工作日 (週一至週五)
        if current_dt.weekday() < 5:  # 0-4 代表週一至週五
            days_moved += day_increment
    
    # 如果起始日期是週末，需要調整到下一個工作日（如果是正向偏移）或前一個工作日（如果是負向偏移）
    if start_dt.weekday() >= 5 and offset_days != 0:
        if offset_days > 0:
            # 找到下一個工作日
            while current_dt.weekday() >= 5:
                current_dt += datetime.timedelta(days=1)
        else:
            # 找到前一個工作日
            while current_dt.weekday() >= 5:
                current_dt -= datetime.timedelta(days=1)
    
    # 轉回原始格式
    result_date = current_dt.strftime("%Y-%m-%d")
    
    # 如果原始格式是民國年或有不同分隔符號，則轉換回去
    if orig_format == "ROC" or orig_separator != "-" or not separator:
        return normalize_date(result_date, orig_format, orig_separator)
    
    return result_date
