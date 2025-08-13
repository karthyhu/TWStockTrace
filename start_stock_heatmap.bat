@echo off
echo Starting Stock Heatmap Environment...
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Switch to stock_realtime_heatmap folder
echo Changing to stock_realtime_heatmap directory...
cd stock_realtime_heatmap

REM Display current location
echo.
echo Current location: %CD%
echo Virtual environment activated, ready to go!
echo.
echo You can now execute the following command to start the application:
echo python twstock_realtime_heatmap.py
echo.

REM Keep command prompt open
cmd /k
