# main.py
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入GUI模块
try:
    from src.gui import VocabularyTutorGUI
    import tkinter as tk
    
    if __name__ == "__main__":
        root = tk.Tk()
        app = VocabularyTutorGUI(root)
        root.mainloop()
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所需依赖: pip install matplotlib pandas openpyxl")
    input("按Enter键退出...")