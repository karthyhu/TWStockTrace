fetch('./../raw_stock_data/daily/today.json')
  .then(response => response.json())
  .then(data => {
    // 顯示日期
    const dateElement = document.querySelector('#stock-date');
    if (dateElement && data.length > 0) {
      // 將民國年轉換為西元年顯示 (1140707 -> 2025/07/07)
      const dateStr = data[0].Date;
      const year = parseInt(dateStr.substring(0, 3)) + 1911; // 民國轉西元
      const month = dateStr.substring(3, 5);
      const day = dateStr.substring(5, 7);
      dateElement.textContent = `資料日期: ${year}/${month}/${day}`;
    }
    
    const tbody = document.querySelector('#stock-table tbody');
    
    // 按照 Range 由高到低排序
    data.sort((a, b) => parseFloat(b.Range) - parseFloat(a.Range));
    
    data.forEach(item => {
      const tr = document.createElement('tr');
      const rangeValue = parseFloat(item.Range);
      let rangeClass = 'neutral';
      if (rangeValue > 0) {
        rangeClass = 'positive';
      } else if (rangeValue < 0) {
        rangeClass = 'negative';
      }
      
      tr.innerHTML = `
        <td>${item.Code}</td>
        <td>${item.Name}</td>
        <td class="${rangeClass}">${rangeValue.toFixed(2)}%</td>
      `;
      tbody.appendChild(tr);
    });
  })
  .catch(error => {
    console.error('載入 JSON 失敗:', error);
  });
