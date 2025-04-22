# wangpancli

多平台网盘命令行工具，提供简单易用的命令行接口，方便在终端中管理您的各类网盘文件。

## 支持的网盘

| 网盘名称 | 网盘类型 | 支持进度 |
|---------|-------|---------|
| 百度网盘 | baidu | 已支持 ✅ |
| 阿里云盘 | aliyun | 计划支持 🚧 |
| 夸克网盘 | quark | 计划支持 🚧 |
| 腾讯微云 | weiyun | 计划支持 🚧 |

更多网盘服务持续添加中...

## 安装

```bash
pip install wangpancli
```

安装后可使用以下任一命令：
- `wangpancli` - 完整命令
- `pancli` - 简写命令
- `wpcli` - 简写命令

## 基本配置

首次使用前需要配置账号信息：

```bash
wangpancli config [网盘类型]
```

例如配置百度网盘：

```bash
wangpancli config baidu
```

配置过程中，您需要提供相应网盘平台所需的授权信息。
对于百度网盘，需要提供：
1. 百度网盘开放平台申请的 AppKey 和 SecretKey
2. 通过生成的授权链接获取的授权码

配置参数获取请参考：[百度网盘开放平台文档](https://pan.baidu.com/union/doc/ol0rsap9s)

## 使用方法

### 查看文件列表

```bash
# 查看本地文件列表
wangpancli ls /local/path

# 查看网盘文件列表（如百度网盘）
wangpancli ls baidu:/remote/path
```

### 复制文件

```bash
# 从本地复制到网盘
wangpancli cp /local/file baidu:/remote/path

# 从网盘下载到本地
wangpancli cp baidu:/remote/file /local/path

# 本地文件复制
wangpancli cp /source/file /dest/path
```

### 创建目录

```bash
# 在本地创建目录
wangpancli mkdir /local/path

# 在网盘创建目录
wangpancli mkdir baidu:/remote/path
```

## 特性

- 支持多种主流网盘服务
- 统一的命令行接口，轻松切换不同网盘
- 支持大文件分片上传
- 支持本地与网盘之间的文件传输
- 支持文件夹批量上传
- 支持命令行彩色输出，区分文件和文件夹
- 提供多个命令别名（wangpancli/pancli/wpcli）

## 依赖

- loguru>=0.7.2
- requests>=2.32.3
- rich>=13.7.0
- Python>=3.10.0

## 许可证

[GNU License](LICENSE)