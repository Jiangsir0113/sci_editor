"""科学编辑编辑加工工具 - 入口"""

import sys
import os

# 确保包路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from sci_editor.gui import main as gui_main
    gui_main()


if __name__ == "__main__":
    main()
