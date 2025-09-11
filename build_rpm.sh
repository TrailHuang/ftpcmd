#!/bin/bash

# FTP工具编译和RPM打包脚本
# 作者: 黄忠雷
# 版本: 1.0.0

set -e  # 遇到错误立即退出

# 脚本配置
SCRIPT_NAME="$(basename "$0")"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="${PROJECT_DIR}/build"
DIST_DIR="${PROJECT_DIR}/dist"
RPM_BUILD_DIR="${PROJECT_DIR}/rpmbuild"

# RPM包配置
PACKAGE_NAME="ftpcmd"
PACKAGE_VERSION="1.0.1"
PACKAGE_RELEASE="1"
PACKAGE_SUMMARY="FTP文件传输工具"
PACKAGE_DESCRIPTION="支持文件/目录上传下载的FTP命令行工具，支持断点续传和进度显示"
PACKAGE_VENDOR="黄忠雷"
PACKAGE_LICENSE="MIT"

# 安装路径配置
INSTALL_BIN_DIR="/usr/local/sbin"
INSTALL_CONFIG_DIR="/usr/local/sbin"

# 颜色输出函数
function print_info() {
    echo -e "\033[32m[INFO] $1\033[0m"
}

function print_warning() {
    echo -e "\033[33m[WARNING] $1\033[0m"
}

function print_error() {
    echo -e "\033[31m[ERROR] $1\033[0m"
    exit 1
}

# 检查依赖工具
function check_dependencies() {
    print_info "检查依赖工具..."
    
    local missing_deps=()
    
    # 检查Python3
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    # 检查PyInstaller - 使用更可靠的方法
    if ! python3 -c "import pkgutil; exit(0 if pkgutil.find_loader('PyInstaller') else 1)" 2>/dev/null; then
        missing_deps+=("pyinstaller")
    fi
    
    # 检查RPM构建工具
    if ! command -v rpmbuild &> /dev/null; then
        missing_deps+=("rpm-build")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "缺少以下依赖: ${missing_deps[*]}"
        print_info "请使用以下命令安装依赖:"
        echo "sudo apt-get update && sudo apt-get install python3 python3-pip rpm"
        echo "sudo pip3 install pyinstaller"
        exit 1
    fi
    
    print_info "所有依赖工具已安装"
}

# 清理构建目录
function clean_build_dirs() {
    print_info "清理构建目录..."
    
    rm -rf "${BUILD_DIR}" "${DIST_DIR}" "${RPM_BUILD_DIR}" 2>/dev/null || true
    mkdir -p "${BUILD_DIR}" "${DIST_DIR}" "${RPM_BUILD_DIR}"
}

# 使用PyInstaller编译Python脚本
function build_binary() {
    print_info "开始编译Python脚本为二进制文件..."
    
    cd "${PROJECT_DIR}"
    
    # 首先确保config.json文件存在
    if [ ! -f "config.json" ]; then
        print_error "配置文件config.json不存在"
    fi
    
    # 使用PyInstaller编译单个文件
    # 使用绝对路径来避免路径问题
    pyinstaller \
        --name="${PACKAGE_NAME}" \
        --onefile \
        --console \
        --add-data "${PROJECT_DIR}/config.json:." \
        --distpath "${DIST_DIR}" \
        --workpath "${BUILD_DIR}" \
        --specpath "${BUILD_DIR}" \
        --hidden-import="argparse" \
        --hidden-import="ftplib" \
        --hidden-import="json" \
        --hidden-import="os" \
        --hidden-import="sys" \
        --hidden-import="pathlib" \
        ftpcmd.py
    
    # 检查编译结果
    if [ ! -f "${DIST_DIR}/${PACKAGE_NAME}" ]; then
        print_error "二进制文件编译失败"
    fi
    
    # 添加执行权限
    chmod +x "${DIST_DIR}/${PACKAGE_NAME}"
    
    print_info "二进制文件编译成功: ${DIST_DIR}/${PACKAGE_NAME}"
}

# 准备RPM构建文件
function prepare_rpm_files() {
    print_info "准备RPM构建文件..."
    
    # 创建RPM构建目录结构
    local rpm_dirs=(
        "${RPM_BUILD_DIR}/SOURCES"
        "${RPM_BUILD_DIR}/SPECS"
        "${RPM_BUILD_DIR}/BUILD"
        "${RPM_BUILD_DIR}/RPMS"
        "${RPM_BUILD_DIR}/SRPMS"
    )
    
    for dir in "${rpm_dirs[@]}"; do
        mkdir -p "${dir}"
    done
    
    # 复制二进制文件到RPM构建目录
    cp "${DIST_DIR}/${PACKAGE_NAME}" "${RPM_BUILD_DIR}/SOURCES/"
    cp "config.json" "${RPM_BUILD_DIR}/SOURCES/"
    
    # 创建源代码tar包
    local source_tar="${RPM_BUILD_DIR}/SOURCES/${PACKAGE_NAME}-${PACKAGE_VERSION}.tar.gz"
    
    # 创建临时目录并复制文件
    local temp_dir="/tmp/${PACKAGE_NAME}-${PACKAGE_VERSION}"
    rm -rf "${temp_dir}" 2>/dev/null || true
    mkdir -p "${temp_dir}"
    
    # 复制项目文件到临时目录
    cp -r "${PROJECT_DIR}"/* "${temp_dir}/" 2>/dev/null || true
    
    # 删除不需要的文件
    rm -rf "${temp_dir}/build" "${temp_dir}/dist" "${temp_dir}/rpmbuild" 2>/dev/null || true
    
    # 创建tar包
    tar -czf "${source_tar}" \
        -C "/tmp" \
        "${PACKAGE_NAME}-${PACKAGE_VERSION}"
    
    # 创建spec文件
    cat > "${RPM_BUILD_DIR}/SPECS/${PACKAGE_NAME}.spec" << EOF
Name: ${PACKAGE_NAME}
Version: ${PACKAGE_VERSION}
Release: ${PACKAGE_RELEASE}%{?dist}
Summary: ${PACKAGE_SUMMARY}

License: ${PACKAGE_LICENSE}
Vendor: ${PACKAGE_VENDOR}
URL: https://github.com/TrailHuang/ftpcmd
Source0: %{name}-%{version}.tar.gz

BuildArch: x86_64

%description
${PACKAGE_DESCRIPTION}

主要功能:
- 文件上传下载
- 目录递归操作
- 断点续传支持
- 实时进度显示
- 配置文件管理

%prep
%setup -q

%build
# 二进制文件已经在外部编译好

%install
# 创建安装目录
mkdir -p %{buildroot}${INSTALL_BIN_DIR}
mkdir -p %{buildroot}${INSTALL_CONFIG_DIR}

# 安装二进制文件 - 直接从SOURCES目录复制
install -m 755 %{_sourcedir}/${PACKAGE_NAME} %{buildroot}${INSTALL_BIN_DIR}/${PACKAGE_NAME}

# 安装配置文件
install -m 644 %{_sourcedir}/config.json %{buildroot}${INSTALL_CONFIG_DIR}/config.json

%files
%defattr(-,root,root,-)
${INSTALL_BIN_DIR}/${PACKAGE_NAME}
${INSTALL_CONFIG_DIR}/config.json

%changelog
* $(date '+%a %b %d %Y') ${PACKAGE_VENDOR} <huangzhonglei@example.com> - ${PACKAGE_VERSION}-${PACKAGE_RELEASE}
- 初始版本发布
- 包含FTP文件传输工具和配置文件

EOF
    
    print_info "RPM构建文件准备完成"
}

# 构建RPM包
function build_rpm() {
    print_info "开始构建RPM包..."
    
    cd "${RPM_BUILD_DIR}/SPECS"
    
    # 设置RPM构建目录
    export TOPDIR="${RPM_BUILD_DIR}"
    
    # 构建RPM包
    rpmbuild -bb \
        --define "_topdir ${TOPDIR}" \
        --define "_sourcedir ${TOPDIR}/SOURCES" \
        --define "_builddir ${TOPDIR}/BUILD" \
        --define "_buildrootdir ${TOPDIR}/BUILDROOT" \
        --define "_rpmdir ${TOPDIR}/RPMS" \
        --define "_srcrpmdir ${TOPDIR}/SRPMS" \
        --define "_specdir ${TOPDIR}/SPECS" \
        ${PACKAGE_NAME}.spec
    
    # 检查RPM包是否生成 - 支持不同的发行版命名格式
    local rpm_patterns=(
        "${RPM_BUILD_DIR}/RPMS/x86_64/${PACKAGE_NAME}-${PACKAGE_VERSION}-${PACKAGE_RELEASE}.*.x86_64.rpm"
        "${RPM_BUILD_DIR}/RPMS/x86_64/${PACKAGE_NAME}-${PACKAGE_VERSION}-${PACKAGE_RELEASE}.x86_64.rpm"
    )
    
    local rpm_file=""
    for pattern in "${rpm_patterns[@]}"; do
        if ls ${pattern} 1> /dev/null 2>&1; then
            rpm_file=$(ls ${pattern})
            break
        fi
    done
    
    if [ -z "${rpm_file}" ]; then
        print_error "RPM包构建失败"
    fi
    
    # 复制RPM包到项目目录
    cp "${rpm_file}" "${PROJECT_DIR}/"
    
    print_info "RPM包构建成功: ${PROJECT_DIR}/$(basename ${rpm_file})"
}

# 显示安装信息
function show_installation_info() {
    local rpm_pattern="${PROJECT_DIR}/${PACKAGE_NAME}-${PACKAGE_VERSION}-${PACKAGE_RELEASE}.*.x86_64.rpm"
    local rpm_file=$(ls ${rpm_pattern} 2>/dev/null || echo "")
    
    if [ -z "${rpm_file}" ]; then
        rpm_pattern="${PROJECT_DIR}/${PACKAGE_NAME}-${PACKAGE_VERSION}-${PACKAGE_RELEASE}.x86_64.rpm"
        rpm_file=$(ls ${rpm_pattern} 2>/dev/null || echo "")
    fi
    
    if [ -z "${rpm_file}" ]; then
        print_error "找不到生成的RPM包"
    fi
    
    cat << EOF

===============================================
FTP工具RPM包构建完成！
===============================================

生成的RPM包: ${rpm_file}

安装命令:
    sudo rpm -ivh $(basename ${rpm_file})

卸载命令:
    sudo rpm -e ${PACKAGE_NAME}

安装位置:
    二进制文件: ${INSTALL_BIN_DIR}/${PACKAGE_NAME}
    配置文件: ${INSTALL_CONFIG_DIR}/config.json

使用说明:
    1. 安装后可直接使用 ${PACKAGE_NAME} 命令
    2. 配置文件位于 ${INSTALL_CONFIG_DIR}/config.json
    3. 可根据需要修改配置文件中的FTP服务器设置

===============================================
EOF
}

# 主函数
function main() {
    print_info "开始FTP工具RPM包构建过程"
    print_info "项目目录: ${PROJECT_DIR}"
    
    # 检查依赖
    check_dependencies
    
    # 清理构建目录
    clean_build_dirs
    
    # 编译二进制文件
    build_binary
    
    # 准备RPM构建文件
    prepare_rpm_files
    
    # 构建RPM包
    build_rpm
    
    # 显示安装信息
    show_installation_info
    
    print_info "RPM包构建过程完成"
}

# 执行主函数
main "$@"