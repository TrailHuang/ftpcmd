# FTP文件传输工具

一个基于Python开发的FTP文件传输命令行工具，支持文件/目录的上传下载、断点续传和实时进度显示。

## 功能特性

- ✅ 支持文件上传和下载
- ✅ 支持目录递归上传和下载
- ✅ 支持断点续传功能
- ✅ 实时传输进度显示
- ✅ 自动创建远程目录结构
- ✅ 支持中文路径和文件名
- ✅ 可配置的连接参数
- ✅ 递归深度限制（防止无限递归卡死）

## 安装要求

- Python 3.6+
- 无需额外依赖（使用标准库ftplib）

## 使用方法

### 基本命令格式

```bash
python ftpcmd.py [选项] --put/--get --local <本地路径> [--remote <远程路径>]
```

### 上传文件/目录

```bash
# 上传单个文件
python ftpcmd.py --put --local /path/to/local/file.txt --remote /remote/path/file.txt

# 上传整个目录
python ftpcmd.py --put --local /path/to/local/directory --remote /remote/path/

# 使用自定义FTP配置
python ftpcmd.py --put --local file.txt --remote /upload/file.txt --host 192.168.1.100 --user username --pass password
```

### 下载文件/目录

```bash
# 下载单个文件
python ftpcmd.py --get --local /path/to/save/file.txt --remote /remote/path/file.txt

# 下载整个目录
python ftpcmd.py --get --local /path/to/save/directory --remote /remote/path/
```

### 所有选项说明

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--put` | 上传模式 | - |
| `--get` | 下载模式 | - |
| `--local` | 本地文件/目录路径 | (必填) |
| `--remote` | 远程文件/目录路径 | `/版本发布区-Manual/clamav_db` |
| `--host` | FTP服务器地址 | `192.168.2.250` |
| `--user` | FTP用户名 | `51` |
| `--pass` | FTP密码 | `51` |
| `--encoding` | FTP连接编码 | `gbk` |

## 安全特性

### 递归深度限制
工具内置了递归深度限制机制（默认50层），防止在处理无限嵌套目录时出现卡死问题。当达到最大递归深度时，工具会安全停止并显示警告信息。

### 实际目录结构处理
工具能够正确处理包含文件的嵌套目录结构，例如：
- `/版本发布区-Manual/clamav_db/test_dir/1/1/1/1.txt` - 在嵌套目录中包含文件
- 同时也能安全处理无限嵌套的目录结构

如果需要调整递归深度限制，可以修改 `download_directory` 方法的 `max_depth` 参数（仅限代码调用）。

## 默认配置

工具内置了以下默认配置，可以通过命令行参数覆盖：

```python
FTP_HOST = '192.168.2.250'    # FTP服务器地址
FTP_USER = '51'               # FTP用户名
FTP_PASS = '51'               # FTP密码
FTP_PATH = '/版本发布区-Manual/clamav_db'  # 默认远程路径
FTP_ENCODING = 'gbk'          # 连接编码
```

## 功能说明

### 断点续传
- 上传时：如果远程文件存在但小于本地文件，会自动从断点处继续上传
- 下载时：如果本地文件存在但小于远程文件，会自动从断点处继续下载
- 支持大文件传输，避免网络中断导致重新传输

### 目录操作
- 支持递归上传整个目录结构
- 自动创建远程目录（如果不存在）
- 保持原有的文件目录结构

### 进度显示
- 实时显示传输进度百分比
- 显示已传输/总字节数
- 支持大文件传输进度跟踪

## 示例

### 示例1：上传病毒库文件

```bash
python ftpcmd.py --put --local /data/clamav/daily.cvd --remote /版本发布区-Manual/clamav_db/
```

### 示例2：下载整个发布目录

```bash
python ftpcmd.py --get --local ./downloads --remote /版本发布区-Manual/clamav_db/
```

### 示例3：使用自定义服务器

```bash
python ftpcmd.py --put --local backup.tar.gz --remote /backups/ --host 10.0.0.100 --user admin --pass secret123
```

## 错误处理

- 连接失败时会显示具体错误信息
- 文件不存在时会提示并退出
- 权限不足时会显示FTP错误代码
- 网络中断时会保持已传输的数据

## 开发说明

工具基于Python标准库`ftplib`开发，主要类：

- `FTPClient`: FTP客户端封装类
- `upload_file()`: 单个文件上传（支持断点续传）
- `download_file()`: 单个文件下载（支持断点续传）
- `upload_directory()`: 目录递归上传
- `download_directory()`: 目录递归下载

## 许可证

MIT License

## 支持

如有问题或建议，请提交Issue或联系开发人员。