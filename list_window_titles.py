#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
窗口标题查看工具
用于列出所有打开的窗口标题，帮助用户准确获取游戏窗口的完整标题
"""

import sys

# 尝试导入必要的库
try:
    import win32gui
except ImportError:
    print("缺少必要的库，请先安装pywin32")
    print("执行命令: pip install pywin32")
    sys.exit(1)

def enum_windows_callback(hwnd, window_list):
    """枚举窗口的回调函数"""
    # 获取窗口标题
    title = win32gui.GetWindowText(hwnd)
    
    # 获取窗口类名
    class_name = win32gui.GetClassName(hwnd)
    
    # 只添加有标题且可见的窗口
    if title and win32gui.IsWindowVisible(hwnd):
        window_list.append((hwnd, title, class_name))

def list_all_windows():
    """列出所有可见的窗口标题"""
    print("=== 窗口标题列表 ===")
    print("以下是所有当前打开的可见窗口标题:")
    print()
    
    # 枚举所有窗口
    window_list = []
    win32gui.EnumWindows(enum_windows_callback, window_list)
    
    # 排序窗口列表（按标题字母顺序）
    window_list.sort(key=lambda x: x[1])
    
    # 打印窗口信息
    for i, (hwnd, title, class_name) in enumerate(window_list, 1):
        print(f"[{i}] 标题: '{title}'")
        print(f"    窗口句柄: {hwnd}")
        print(f"    窗口类: {class_name}")
        print()
    
    print(f"共找到 {len(window_list)} 个可见窗口")
    print("\n提示: 启动游戏后运行此脚本，找到游戏窗口的标题并复制完整文本")
    print("然后在远程控制服务器启动时粘贴这个完整标题")

def search_window_by_keyword(keyword):
    """根据关键词搜索窗口"""
    print(f"=== 搜索标题包含 '{keyword}' 的窗口 ===")
    
    window_list = []
    win32gui.EnumWindows(enum_windows_callback, window_list)
    
    # 过滤包含关键词的窗口
    filtered_windows = [(hwnd, title, class_name) for hwnd, title, class_name in window_list 
                       if keyword.lower() in title.lower()]
    
    if filtered_windows:
        for i, (hwnd, title, class_name) in enumerate(filtered_windows, 1):
            print(f"[{i}] 标题: '{title}'")
            print(f"    窗口句柄: {hwnd}")
            print(f"    窗口类: {class_name}")
            print()
        print(f"共找到 {len(filtered_windows)} 个匹配窗口")
    else:
        print(f"未找到标题包含 '{keyword}' 的窗口")

def main():
    """主函数"""
    print("游戏窗口标题查看工具 v1.0")
    print("=====================")
    print()
    
    # 如果有命令行参数，则用作搜索关键词
    if len(sys.argv) > 1:
        keyword = sys.argv[1]
        search_window_by_keyword(keyword)
    else:
        # 否则列出所有窗口
        list_all_windows()
    
    print("\n使用方法:")
    print("  1. 运行游戏")
    print("  2. 运行此脚本查看所有窗口标题")
    print("  3. 找到游戏窗口，复制其完整标题")
    print("  4. 在远程控制服务器启动时粘贴此标题")
    print("\n或者使用命令搜索特定窗口:")
    print("  python list_window_titles.py 关键词")
    print("例如:")
    print("  python list_window_titles.py 游戏")
    
    input("\n按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"发生错误: {e}")
        input("按回车键退出...")