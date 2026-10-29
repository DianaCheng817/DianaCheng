@echo off
chcp 65001 >nul
title 顺序表作业 - 自动运行
echo ============================================
echo   顺序表作业：一键运行脚本
echo   将依次运行 playlist.py 和 fix_table3.py
echo   所有结果输出到本脚本所在目录
echo ============================================
echo.
echo [1/2] 正在运行 playlist.py（生成表1/表2/表3/自测/十万条数据，约1-2分钟）...
echo.
python "%~dp0playlist.py"
echo.
echo [2/2] 正在运行 fix_table3.py（复核 table3 搬移计数）...
echo.
python "%~dp0fix_table3.py"
echo.
echo ============================================
echo   全部运行完成！结果文件在本脚本所在目录：
echo   table1.csv / table2.csv / table3.csv / selftest.csv
echo   songs_100000.txt / 运行日志_playlist.txt
echo ============================================
pause
