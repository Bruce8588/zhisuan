#!/usr/bin/env python3
"""
iFinDPy 自动化安装脚本
功能：自动下载并安装 iFinDPy
"""
import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path


def install_ifindpy(username, password):
    """自动化安装 iFinDPy"""
    
    print("=== iFinDPy 自动化安装 ===\n")
    
    # 1. 检查是否已安装
    try:
        from iFinDPy import THS_iFinDLogin
        print("✓ iFinDPy 已安装")
        
        # 测试登录
        result = THS_iFinDLogin(username, password)
        if result == 0 or result is True:
            print("✓ 登录成功！")
        else:
            print(f"✗ 登录失败，请检查账号密码")
        return True
    except ImportError:
        print("iFinDPy 未安装，开始安装...")
    except Exception as e:
        print(f"iFinDPy 导入失败: {e}")
        print("需要重新安装")
    
    # 2. 下载 iFinDPy
    download_url = "https://quant.10jqka.com.cn/api/download/ifindpy"
    download_path = "/tmp/iFinDPy.zip"
    
    print(f"\n正在下载 iFinDPy...")
    print(f"下载地址: {download_url}")
    
    try:
        # 尝试下载
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        req = urllib.request.Request(download_url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as response:
            with open(download_path, 'wb') as f:
                shutil.copyfileobj(response, f)
        print(f"✓ 下载完成: {download_path}")
        
    except Exception as e:
        print(f"✗ 下载失败: {e}")
        print("\n请手动下载:")
        print(f"1. 登录 https://quant.10jqka.com.cn/")
        print(f"2. 进入 个人中心 → 本地SDK")
        print(f"3. 下载 iFinDPy Python接口")
        print(f"4. 将下载的文件放到: {download_path}")
        return False
    
    # 3. 解压安装
    print("\n正在安装...")
    try:
        # 解压
        extract_dir = "/tmp/iFinDPy"
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        
        with zipfile.ZipFile(download_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # 查找安装脚本
        install_script = None
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                if 'install' in f.lower() or f.endswith('.py'):
                    install_script = os.path.join(root, f)
                    break
        
        if install_script:
            print(f"找到安装脚本: {install_script}")
            # 执行安装
            result = subprocess.run([sys.executable, install_script], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                print("✓ 安装成功！")
            else:
                print(f"安装输出: {result.stdout}")
                print(f"安装错误: {result.stderr}")
        
        # 尝试 pip 安装
        print("\n尝试 pip 安装...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', extract_dir, '-q'],
                             capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ pip 安装成功！")
        else:
            print(f"pip 安装失败: {result.stderr}")
            
    except Exception as e:
        print(f"✗ 安装失败: {e}")
        return False
    
    # 4. 验证安装
    print("\n验证安装...")
    try:
        from iFinDPy import THS_iFinDLogin
        print("✓ iFinDPy 导入成功！")
        
        # 测试登录
        print(f"\n测试登录账号: {username}")
        result = THS_iFinDLogin(username, password)
        if result == 0 or result is True:
            print("✓ 登录成功！")
            return True
        else:
            print(f"✗ 登录失败，请检查账号密码")
            return False
            
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        print("\n请手动安装:")
        print(f"1. 解压 {download_path}")
        print(f"2. 运行解压目录中的安装脚本")
        return False


if __name__ == "__main__":
    username = "gdjgss003"
    password = "0guB2W60"
    
    success = install_ifindpy(username, password)
    
    if success:
        print("\n=== 安装完成 ===")
        print("现在可以使用 iFinDPy 获取数据了")
    else:
        print("\n=== 安装失败 ===")
        print("请查看上述错误信息或手动安装")
