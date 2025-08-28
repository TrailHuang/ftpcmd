#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FTP文件传输工具
支持文件/目录的上传与下载，支持断点续传和实时进度反馈
"""

import os
import sys
import argparse
import ftplib
import time
from pathlib import Path
from typing import Optional, Tuple


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
            self.ftp = ftplib.FTP(self.host, encoding=self.encoding)
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
                    print(f"本地路径不是文件: {local_file}")
                    return False
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
                return False
            
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


def main():
    """主函数，处理命令行参数并执行相应操作"""
    
    FTP_HOST = '192.168.2.250'
    FTP_USER = '51'
    FTP_PASS = '51'
    FTP_PATH = '/文件中转区/恶意程序现网分析/20250828'
    FTP_ENCODING = 'gbk'
    
    parser = argparse.ArgumentParser(description='FTP文件传输工具')
    parser.add_argument('--put', action='store_true', help='上传文件/目录到FTP服务器')
    parser.add_argument('--get', action='store_true', help='从FTP服务器下载文件/目录')
    parser.add_argument('--ls', action='store_true', help='列出FTP服务器文件列表')
    parser.add_argument('--local', help='本地文件/目录路径（下载时可省略，默认为当前目录）')
    parser.add_argument('--remote', help='远程文件/目录路径（默认为FTP_PATH）')
    parser.add_argument('--host', default=FTP_HOST, help=f'FTP服务器地址（默认: {FTP_HOST}）')
    parser.add_argument('--user', default=FTP_USER, help=f'FTP用户名（默认: {FTP_USER}）')
    parser.add_argument('--pass', dest='password', default=FTP_PASS, help=f'FTP密码（默认: {FTP_PASS}）')
    parser.add_argument('--encoding', default=FTP_ENCODING, help=f'FTP连接编码（默认: {FTP_ENCODING}）')
    
    args = parser.parse_args()
    
    if not (args.put or args.get or args.ls):
        print("错误: 必须指定 --put、--get 或 --ls 参数")
        parser.print_help()
        sys.exit(1)
    
    action_count = sum([args.put, args.get, args.ls])
    if action_count > 1:
        print("错误: --put、--get 和 --ls 参数不能同时使用")
        sys.exit(1)
    
    if args.remote:
        remote_path = os.path.join(FTP_PATH, args.remote).replace('\\', '/')
    else:
        remote_path = FTP_PATH
    
    ftp_client = FTPClient(args.host, args.user, args.password, args.encoding)
    
    try:
        if not ftp_client.connect():
            sys.exit(1)
        
        if args.ls:
            success = ftp_client.list_directory(remote_path)
        elif args.put:
            local_path = Path(args.local)
            if local_path.is_file():
                if '.' in os.path.basename(remote_path) or remote_path.endswith('/'):
                    remote_file = remote_path
                else:
                    remote_file = os.path.join(remote_path, local_path.name).replace('\\', '/')
                success = ftp_client.upload_file(args.local, remote_file)
            elif local_path.is_dir():
                remote_dir = os.path.join(remote_path, local_path.name).replace('\\', '/')
                success = ftp_client.upload_directory(args.local, remote_dir)
            else:
                print(f"本地路径不存在: {args.local}")
                success = False
        
        else:
            if not args.remote:
                print("错误: 下载操作必须指定 --remote 参数")
                sys.exit(1)
            
            if args.local:
                local_path = Path(args.local)
            else:
                local_path = Path(".")
            
            try:
                ftp_client.ftp.size(remote_path)
                is_file = True
            except:
                is_file = False
            
            if is_file:
                if args.local:
                    local_file = args.local
                else:
                    local_file = os.path.basename(remote_path)
                success = ftp_client.download_file(remote_path, local_file)
            else:
                if args.local:
                    local_dir = args.local
                else:
                    local_dir = os.path.basename(remote_path) or "downloaded"
                success = ftp_client.download_directory(remote_path, local_dir)
        
        sys.exit(0 if success else 1)
        
    finally:
        ftp_client.disconnect()


if __name__ == '__main__':
    main()