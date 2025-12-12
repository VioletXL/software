# run_recommendation.py
import subprocess
import sys


def main():
    # 确保使用虚拟环境的Python
    python_path = sys.executable

    # 启动API服务
    print("启动推荐API服务...")
    subprocess.run([python_path, "code/api.py"])


if __name__ == "__main__":
    main()