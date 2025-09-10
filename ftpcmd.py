#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTP文件传输工具
支持文件/目录的上传与下载，支持断点续传和实时进度反馈
"""

# 版本号
VERSION = "1.0.1"

import os
import sys
import argparse
import ftplib
import json
from pathlib import Path


class FTPClient:
    """FTP客户端类，封装FTP连接和文件操作"""
    
    def __init__(self, host: str, username: str, password: str, encoding: str = 'gbk'):
        """
        初始化FTP客户端
        
        Args:
            host: FTP服务器地址
            username: FTP用户名
            password: FTP密码
            encoding: FTP连接编码，默认为'gbk'
        """
        self.host = host
        self.username = username
        self.password = password
        self.encoding = encoding
        self.ftp = None
        self.connected = False
    
    def connect(self) -> bool:
        """
        连接到FTP服务器
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 兼容不同Python版本的FTP连接方式
            try:
                # Python 3.9+ 支持encoding参数
                self.ftp = ftplib.FTP(self.host, encoding=self.encoding)
            except TypeError:
                # Python 3.8及以下版本不支持encoding参数
                self.ftp = ftplib.FTP(self.host)
                # 手动设置编码
                self.ftp.encoding = self.encoding
            
            self.ftp.login(self.username, self.password)
            self.connected = True
            print(f"成功连接到FTP服务器: {self.host}")
            return True
        except Exception as e:
            print(f"连接FTP服务器失败: {e}")
            return False
    
    def disconnect(self):
        """断开FTP连接"""
        if self.ftp and self.connected:
            try:
                self.ftp.quit()
            except:
                self.ftp.close()
            finally:
                self.connected = False
                print("已断开FTP连接")
    
    def ensure_remote_directory(self, remote_path: str) -> bool:
        """
        确保远程目录存在，如果不存在则创建
        
        Args:
            remote_path: 远程目录路径
            
        Returns:
            bool: 目录是否存在或创建成功
        """
        try:
            self.ftp.cwd('/')
            
            directories = [d for d in remote_path.split('/') if d]
            for directory in directories:
                try:
                    self.ftp.cwd(directory)
                except:
                    self.ftp.mkd(directory)
                    self.ftp.cwd(directory)
            
            return True
        except Exception as e:
            print(f"创建远程目录失败: {e}")
            return False
    
    def upload_file(self, local_file: str, remote_file: str) -> bool:
        """
        上传单个文件到FTP服务器，支持断点续传
        
        Args:
            local_file: 本地文件路径
            remote_file: 远程文件路径
            
        Returns:
            bool: 上传是否成功
        """
        try:
            local_path = Path(local_file)
            if not local_path.is_file():
                print(f"本地文件不存在: {local_file}")
                return False
            
           
            file_size = local_path.stat().st_size
            
            
            remote_size = 0
            try:
                remote_size = self.ftp.size(remote_file)
            except:
                remote_size = 0
            
            
            if remote_size > 0 and remote_size < file_size:
                print(f"发现未完成的上传，继续从 {remote_size} 字节处上传")
                mode = 'ab'
                start_pos = remote_size
            else:
                mode = 'wb'
                start_pos = 0
            
            
            remote_dir = os.path.dirname(remote_file)
            if remote_dir and not self.ensure_remote_directory(remote_dir):
                return False
            
            
            with open(local_file, 'rb') as f:
                if start_pos > 0:
                    f.seek(start_pos)
                
                def callback(data):
                    nonlocal start_pos
                    start_pos += len(data)
                    progress = (start_pos / file_size) * 100
                    sys.stdout.write(f"\r上传进度: {progress:.1f}% ({start_pos}/{file_size} bytes)")
                    sys.stdout.flush()
                
                self.ftp.storbinary(f"STOR {remote_file}", f, blocksize=8192, callback=callback, rest=start_pos)
            
            print(f"\n文件上传成功: {local_file} -> {remote_file}")
            return True
            
        except Exception as e:
            print(f"\n文件上传失败: {e}")
            return False
    
    def list_directory(self, remote_dir: str = '/') -> bool:

        try:
            self.ftp.cwd(remote_dir)
            
            items = []
            self.ftp.retrlines('LIST', items.append)
            
            if not items:
                print(f"目录 '{remote_dir}' 为空")
                return True
            
            print(f"目录 '{remote_dir}' 的内容:")
            print("-" * 80)
            
            for item in items:
                parts = item.split()
                if len(parts) < 3:
                    continue
                
                is_dir = parts[0].startswith('d') if parts[0] else False
                file_size = parts[4] if len(parts) >= 5 else "-"
                
                time_parts = parts[5:8] if len(parts) >= 8 else []
                mod_time = ' '.join(time_parts) if time_parts else "-"
                
                filename = ' '.join(parts[8:]) if len(parts) >= 9 else parts[-1]
                
                if filename in ['.', '..']:
                    continue
                
                file_type = "DIR" if is_dir else "FILE"
                print(f"{file_type:4} {file_size:>10} {mod_time:12} {filename}")
            
            print("-" * 80)
            return True
            
        except Exception as e:
            print(f"列出目录失败: {e}")
            return False

    def download_file(self, remote_file: str, local_file: str) -> bool:

        try:
            try:
                remote_size = self.ftp.size(remote_file)
                if remote_size is None:
                    print(f"远程文件不存在: {remote_file}")
                    return False
            except:
                print(f"远程文件不存在: {remote_file}")
                return False
            
            local_path = Path(local_file)
            
            local_size = 0
            if local_path.exists():
                if local_path.is_file():
                    local_size = local_path.stat().st_size
                    if local_size == remote_size:
                        print(f"文件已存在且完整: {local_file}")
                        return True
                    elif local_size < remote_size:
                        print(f"发现未完成的下载，继续从 {local_size} 字节处下载")
                        mode = 'ab'
                        start_pos = local_size
                    else:
                        print(f"本地文件异常，重新下载")
                        mode = 'wb'
                        start_pos = 0
                else:
                    # 如果本地路径是目录，则将文件下载到该目录中
                    local_file = os.path.join(local_file, os.path.basename(remote_file))
                    local_path = Path(local_file)
                    if local_path.exists() and local_path.is_file():
                        local_size = local_path.stat().st_size
                        if local_size == remote_size:
                            print(f"文件已存在且完整: {local_file}")
                            return True
                        elif local_size < remote_size:
                            print(f"发现未完成的下载，继续从 {local_size} 字节处下载")
                            mode = 'ab'
                            start_pos = local_size
                        else:
                            print(f"本地文件异常，重新下载")
                            mode = 'wb'
                            start_pos = 0
                    else:
                        mode = 'wb'
                        start_pos = 0
            else:
                mode = 'wb'
                start_pos = 0
            
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(local_file, mode) as f:
                def callback(data):
                    """下载进度回调函数"""
                    nonlocal start_pos
                    f.write(data)
                    start_pos += len(data)
                    progress = (start_pos / remote_size) * 100
                    sys.stdout.write(f"\r下载进度: {progress:.1f}% ({start_pos}/{remote_size} bytes)")
                    sys.stdout.flush()
                
                self.ftp.retrbinary(f"RETR {remote_file}", callback, blocksize=8192, rest=start_pos)
            
            print(f"\n文件下载成功: {remote_file} -> {local_file}")
            return True
            
        except Exception as e:
            print(f"\n文件下载失败: {e}")
            return False
    
    def upload_directory(self, local_dir: str, remote_dir: str) -> bool:
        """
        上传整个目录到FTP服务器
        
        Args:
            local_dir: 本地目录路径
            remote_dir: 远程目录路径
            
        Returns:
            bool: 上传是否成功
        """
        try:
            local_path = Path(local_dir)
            if not local_path.is_dir():
                print(f"本地目录不存在: {local_dir}")
                return False
            
            if not self.ensure_remote_directory(remote_dir):
                return False
            
            print(f"开始上传目录: {local_dir} -> {remote_dir}")
            
            success_count = 0
            total_count = 0
            
            for root, dirs, files in os.walk(local_dir):
                relative_path = os.path.relpath(root, local_dir)
                if relative_path == '.':
                    relative_path = ''
                
                current_remote_dir = os.path.join(remote_dir, relative_path).replace('\\', '/')
                
                self.ensure_remote_directory(current_remote_dir)
                
                for file in files:
                    local_file = os.path.join(root, file)
                    remote_file = os.path.join(current_remote_dir, file).replace('\\', '/')
                    
                    total_count += 1
                    print(f"\n[{total_count}] 上传文件: {file}")
                    
                    if self.upload_file(local_file, remote_file):
                        success_count += 1
            
            print(f"\n目录上传完成: {success_count}/{total_count} 个文件成功")
            return success_count == total_count
            
        except Exception as e:
            print(f"目录上传失败: {e}")
            return False
    
    def download_directory(self, remote_dir: str, local_dir: str, max_depth: int = 50) -> bool:
        """
        从FTP服务器下载整个目录
        
        Args:
            remote_dir: 远程目录路径
            local_dir: 本地目录路径
            max_depth: 最大递归深度，防止无限递归
            
        Returns:
            bool: 下载是否成功
        """
        try:
            try:
                self.ftp.cwd(remote_dir)
            except:
                print(f"远程目录不存在: {remote_dir}")
                return True
            
            print(f"开始下载目录: {remote_dir} -> {local_dir}")
            
            success_count = 0
            total_count = 0
            
            def download_recursive(current_remote_dir, current_local_dir, depth):
                nonlocal success_count, total_count
                
                if depth > max_depth:
                    print(f"警告: 达到最大递归深度 {max_depth}，停止下载")
                    return
                
                Path(current_local_dir).mkdir(parents=True, exist_ok=True)
                
                try:
                    self.ftp.cwd(current_remote_dir)
                    
                    items = []
                    self.ftp.retrlines('LIST', items.append)
                    

                    
                    for item in items:
                        parts = item.split()
                        if len(parts) < 3:
                            continue
                        
                        is_dir = parts[0].startswith('d') if parts[0] else False
                        
                        filename = ' '.join(parts[8:]) if len(parts) >= 9 else parts[-1]
                        
                        if filename in ['.', '..']:
                            continue
                        

                        
                        remote_path = os.path.join(current_remote_dir, filename).replace('\\', '/')
                        local_path = os.path.join(current_local_dir, filename)
                        
                        if is_dir:
                            download_recursive(remote_path, local_path, depth + 1)
                        else:
                            total_count += 1
                            if self.download_file(remote_path, local_path):
                                success_count += 1
                
                except Exception as e:
                    print(f"获取目录列表失败: {e}")
                    import traceback
                    print(f"详细错误: {traceback.format_exc()}")
            
            download_recursive(remote_dir, local_dir, 0)
            
            print(f"\n目录下载完成: {success_count}/{total_count} 个文件成功")
            return success_count == total_count
            
        except Exception as e:
            print(f"目录下载失败: {e}")
            return False

    def tree_directory(self, remote_dir: str = '/', max_depth: int = 10, current_depth: int = 0) -> bool:
        """
        以树状结构显示FTP服务器目录
        
        Args:
            remote_dir: 远程目录路径
            max_depth: 最大递归深度
            current_depth: 当前递归深度
            
        Returns:
            bool: 显示是否成功
        """
        try:
            if current_depth > max_depth:
                print(f"  {'  ' * current_depth}└── [达到最大深度 {max_depth}]")
                return True
            
            try:
                self.ftp.cwd(remote_dir)
            except:
                print(f"远程目录不存在: {remote_dir}")
                return True
            
            items = []
            self.ftp.retrlines('LIST', items.append)
            
            if not items:
                print(f"  {'  ' * current_depth}└── (空目录)")
                return True
            
            # 显示当前目录
            if current_depth == 0:
                print(f"{remote_dir}/")
            else:
                dir_name = os.path.basename(remote_dir.rstrip('/'))
                print(f"  {'  ' * (current_depth - 1)}├── {dir_name}/")
            
            dirs = []
            files = []
            
            for item in items:
                parts = item.split()
                if len(parts) < 3:
                    continue
                
                is_dir = parts[0].startswith('d') if parts[0] else False
                filename = ' '.join(parts[8:]) if len(parts) >= 9 else parts[-1]
                
                if filename in ['.', '..']:
                    continue
                
                if is_dir:
                    dirs.append(filename)
                else:
                    files.append(filename)
            
            # 先显示文件
            for i, file in enumerate(sorted(files)):
                is_last_file = i == len(files) - 1 and not dirs
                prefix = "  " + ("  " * current_depth) + ("└── " if is_last_file else "├── ")
                print(f"{prefix}{file}")
            
            # 再递归显示目录
            for i, directory in enumerate(sorted(dirs)):
                is_last_dir = i == len(dirs) - 1
                prefix = "  " + ("  " * current_depth) + ("└── " if is_last_dir else "├── ")
                print(f"{prefix}{directory}/")
                
                sub_remote_dir = os.path.join(remote_dir, directory).replace('\\', '/')
                self.tree_directory(sub_remote_dir, max_depth, current_depth + 1)
            
            return True
            
        except Exception as e:
            print(f"显示目录树失败: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
            return False


def load_config(path="config.json"):
    """
    从config.json文件加载配置
    
    Returns:
        dict: 配置字典，如果文件不存在则返回None
    """
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    
    if not os.path.exists(config_file):
        return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return None


def main():
    """主函数，处理命令行参数并执行相应操作"""
    
    # 从配置文件加载配置
    config = load_config("/usr/local/sbin/config.json")
    
    # 设置默认配置
    FTP_HOST = config.get('FTP_HOST', '192.168.2.250') if config else '192.168.2.250'
    FTP_USER = config.get('FTP_USER', '51') if config else '51'
    FTP_PASS = config.get('FTP_PASS', '51') if config else '51'
    FTP_PATH = config.get('FTP_PATH', '/文件中转区/研发一部/黄忠雷') if config else '/文件中转区/研发一部/黄忠雷'
    FTP_ENCODING = config.get('FTP_ENCODING', 'gbk') if config else 'gbk'
    
    parser = argparse.ArgumentParser(description='FTP文件传输工具')
    parser.add_argument('-p','--put', nargs='?', const=True, help='上传文件/目录到FTP服务器，后接本地路径')
    parser.add_argument('-g','--get', nargs='?', const=True, help='从FTP服务器下载文件/目录，后接远程路径')
    parser.add_argument('--ls', nargs='?', const=True, help='列出FTP服务器文件列表，后接远程路径')
    parser.add_argument('--tree', nargs='?', const=True, help='以树状结构显示FTP服务器目录，后接远程路径')
    parser.add_argument('-l', '--local', help='本地文件/目录路径')
    parser.add_argument('-r', '--remote', help='远程文件/目录路径')
    parser.add_argument('--host', default=FTP_HOST, help=f'FTP服务器地址（默认: {FTP_HOST}）')
    parser.add_argument('--user', default=FTP_USER, help=f'FTP用户名（默认: {FTP_USER}）')
    parser.add_argument('--pass', dest='password', default=FTP_PASS, help=f'FTP密码（默认: {FTP_PASS}）')
    parser.add_argument('--encoding', default=FTP_ENCODING, help=f'FTP连接编码（默认: {FTP_ENCODING}）')
    parser.add_argument('-v', '--version', action='store_true', help='显示版本信息')
    
    args = parser.parse_args()
    
    # 处理版本显示
    if args.version:
        print(f"FTP文件传输工具 v{VERSION}")
        sys.exit(0)
    
    # 检查是否有操作参数
    has_action = bool(args.put or args.get or args.ls or args.tree)
    if not has_action:
        print("错误: 必须指定 --put、--get、--ls、--tree 或 --version 参数")
        parser.print_help()
        sys.exit(1)
    
    # 检查参数冲突
    action_count = sum([bool(args.put), bool(args.get), bool(args.ls), bool(args.tree)])
    if action_count > 1:
        print("错误: --put、--get、--ls 和 --tree 参数不能同时使用")
        sys.exit(1)
    
    # 检查参数组合冲突
    if args.put and args.local:
        print("错误: --put 命令不需要使用 --local 参数")
        sys.exit(1)
    
    if args.get and args.remote:
        print("错误: --get 命令不需要使用 --remote 参数")
        sys.exit(1)
    
    # 处理远程路径
    if args.remote:
        # 如果远程路径已经是绝对路径（以/开头），则直接使用
        if args.remote.startswith('/'):
            remote_path = args.remote
        else:
            remote_path = os.path.join(FTP_PATH, args.remote).replace('\\', '/')
    else:
        remote_path = FTP_PATH
    
    # 处理新的参数格式：--put 后直接跟本地路径
    if args.put and args.put is not True:
        args.local = args.put
        args.put = True
    
    # 处理新的参数格式：--get 后直接跟远程路径
    if args.get and args.get is not True:
        args.remote = args.get
        args.get = True
        # 重新处理远程路径，因为args.remote已经改变
        if args.remote.startswith('/'):
            remote_path = args.remote
        else:
            remote_path = os.path.join(FTP_PATH, args.remote).replace('\\', '/')
    
    # 处理新的参数格式：--ls 后直接跟远程路径
    if args.ls and args.ls is not True:
        args.remote = args.ls
        args.ls = True
        # 重新处理远程路径，因为args.remote已经改变
        if args.remote.startswith('/'):
            remote_path = args.remote
        else:
            remote_path = os.path.join(FTP_PATH, args.remote).replace('\\', '/')
    
    # 处理新的参数格式：--tree 后直接跟远程路径
    if args.tree and args.tree is not True:
        args.remote = args.tree
        args.tree = True
        # 重新处理远程路径，因为args.remote已经改变
        if args.remote.startswith('/'):
            remote_path = args.remote
        else:
            remote_path = os.path.join(FTP_PATH, args.remote).replace('\\', '/')
    
    ftp_client = FTPClient(args.host, args.user, args.password, args.encoding)
    
    try:
        if not ftp_client.connect():
            sys.exit(1)
        
        if args.ls:
            success = ftp_client.list_directory(remote_path)
        elif args.tree:
            success = ftp_client.tree_directory(remote_path)
        elif args.put:
            if not args.local:
                print("错误: --put 操作需要指定本地路径")
                success = False
            else:
                local_path = Path(args.local)
                if local_path.is_file():
                    # 如果远程路径以/结尾，表示要在该目录下创建文件
                    if remote_path.endswith('/'):
                        # 确保目录存在
                        remote_dir = remote_path.rstrip('/')
                        if not ftp_client.ensure_remote_directory(remote_dir):
                            success = False
                        else:
                            remote_file = os.path.join(remote_dir, local_path.name).replace('\\', '/')
                            success = ftp_client.upload_file(args.local, remote_file)
                    else:
                        # 如果远程路径是目录路径（以/结尾），则使用本地文件名
                        if remote_path == FTP_PATH or remote_path.endswith('/'):
                            remote_file = os.path.join(remote_path, local_path.name).replace('\\', '/')
                            success = ftp_client.upload_file(args.local, remote_file)
                        else:
                            # 直接使用指定的远程路径（重命名文件）
                            success = ftp_client.upload_file(args.local, remote_path)
                elif local_path.is_dir():
                    # 如果远程路径以/结尾，表示要在该目录下创建子目录
                    if remote_path.endswith('/'):
                        # 确保父目录存在
                        remote_parent_dir = remote_path.rstrip('/')
                        if not ftp_client.ensure_remote_directory(remote_parent_dir):
                            success = False
                        else:
                            remote_dir = os.path.join(remote_parent_dir, local_path.name).replace('\\', '/')
                            success = ftp_client.upload_directory(args.local, remote_dir)
                    else:
                        # 直接使用指定的远程路径（重命名目录）
                        success = ftp_client.upload_directory(args.local, remote_path)
                else:
                    print(f"本地路径不存在: {args.local}")
                    success = False
        
        else:
            if not args.remote:
                print("错误: 下载操作必须指定远程路径")
                success = False
            else:
                if args.local:
                    local_path = Path(args.local)
                else:
                    local_path = Path(".")
                
                # 使用更可靠的方法判断文件/目录类型
                # 尝试切换到该路径，如果能切换成功说明是目录
                try:
                    ftp_client.ftp.cwd(remote_path)
                    is_file = False  # 能切换到该路径，说明是目录
                    ftp_client.ftp.cwd('/')  # 切换回根目录
                    print(f"DEBUG: 路径 {remote_path} 是目录")
                except:
                    # 不能切换，可能是文件或不存在的路径
                    # 尝试获取文件大小来判断是否是文件
                    try:
                        ftp_client.ftp.size(remote_path)
                        is_file = True  # 能获取文件大小，说明是文件
                        print(f"DEBUG: 路径 {remote_path} 是文件")
                    except:
                        # 既不能切换目录也不能获取文件大小，说明路径不存在
                        print(f"错误: 远程路径不存在: {remote_path}")
                        success = False
                        is_file = None  # 标记为无效路径
                
                if is_file:
                    if args.local:
                        # 如果本地路径以/结尾，表示要创建目录并下载到该目录
                        if args.local.endswith('/'):
                            # 创建目录并下载文件到该目录
                            os.makedirs(args.local, exist_ok=True)
                            local_file = os.path.join(args.local, os.path.basename(remote_path))
                        else:
                            # 直接使用指定的本地路径（重命名文件）
                            local_file = args.local
                    else:
                        local_file = os.path.basename(remote_path)
                    success = ftp_client.download_file(remote_path, local_file)
                else:
                    if args.local:
                        # 如果本地路径以/结尾，表示要创建目录并下载到该目录
                        if args.local.endswith('/'):
                            # 创建目录并下载目录内容到该目录
                            os.makedirs(args.local, exist_ok=True)
                            local_dir = os.path.join(args.local, os.path.basename(remote_path))
                        else:
                            # 直接使用指定的本地路径（重命名目录）
                            local_dir = args.local
                    else:
                        local_dir = os.path.basename(remote_path) or "downloaded"
                    success = ftp_client.download_directory(remote_path, local_dir)
        
        sys.exit(0 if success else 1)
        
    finally:
        ftp_client.disconnect()


if __name__ == '__main__':
    main()