@echo off
echo Starting Stock Heatmap Application...
echo.

REM Activate virtual environment and switch to target folder
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Changing to stock_realtime_heatmap directory...
cd stock_realtime_heatmap

REM Execute the program directly
echo.
echo Starting Stock Heatmap Application...
echo Application will run at http://127.0.0.1:8050/
echo.
python twstock_realtime_heatmap.py

REM If the program ends, keep the window open
pause
