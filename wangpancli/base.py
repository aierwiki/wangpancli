import argparse
import requests
import json
import os
import random
from urllib.parse import urlencode
from .baidu_pan_sdk import BaiduPanSDK
from loguru import logger


class WangPanCLI():
    ACCOUNT_CONFIG_FILE = os.path.expanduser('~/.cache/wangpancli/account_info.json')
    
    # 支持的网盘类型及对应的SDK
    PAN_SDK_MAP = {
        'baidu': BaiduPanSDK,
        # 未来可以添加其他网盘的SDK
        # 'aliyun': AliyunPanSDK,
        # 'quark': QuarkPanSDK,
        # 'weiyun': WeiyunPanSDK,
    }
    
    def __init__(self):
        self.account_info = {}
        self.sdk_instances = {}  # 用于存储各种网盘SDK的实例
        
        # 确保配置目录存在
        if not os.path.exists(os.path.dirname(WangPanCLI.ACCOUNT_CONFIG_FILE)):
            os.makedirs(os.path.dirname(WangPanCLI.ACCOUNT_CONFIG_FILE))
    
    def get_sdk(self, pan_type):
        """获取指定类型网盘的SDK实例"""
        if pan_type not in self.sdk_instances:
            if pan_type in self.PAN_SDK_MAP:
                self.sdk_instances[pan_type] = self.PAN_SDK_MAP[pan_type]()
            else:
                raise ValueError(f"不支持的网盘类型: {pan_type}")
        return self.sdk_instances[pan_type]
    
    def load_config(self, pan_type=None):
        """加载特定类型网盘的配置信息"""
        if not os.path.exists(WangPanCLI.ACCOUNT_CONFIG_FILE):
            logger.debug(f"{WangPanCLI.ACCOUNT_CONFIG_FILE} not exist!")
            return False
            
        with open(WangPanCLI.ACCOUNT_CONFIG_FILE, 'r') as f:
            all_accounts = json.load(f)
        
        # 如果指定了网盘类型，只检查该类型的配置
        if pan_type:
            if pan_type not in all_accounts:
                logger.debug(f"{pan_type} 配置不存在")
                return False
                
            account_info = all_accounts[pan_type]
            required_keys = ['AppKey', 'SecretKey', 'refreshToken', 'accessToken']
            for key in required_keys:
                if key not in account_info:
                    logger.debug(f"{key} not in {pan_type} account_info")
                    return False
                    
            self.account_info[pan_type] = account_info
            return True
        else:
            # 加载所有配置
            has_valid_config = False
            for pan_type, account_info in all_accounts.items():
                required_keys = ['AppKey', 'SecretKey', 'refreshToken', 'accessToken']
                valid = True
                for key in required_keys:
                    if key not in account_info:
                        valid = False
                        break
                        
                if valid:
                    self.account_info[pan_type] = account_info
                    has_valid_config = True
                    
            return has_valid_config

    def handle_config(self, pan_type='baidu'):
        """配置特定类型网盘的账户信息"""
        if pan_type not in self.PAN_SDK_MAP:
            print(f"暂不支持 {pan_type} 网盘类型")
            return
            
        sdk = self.get_sdk(pan_type)
        
        if pan_type == 'baidu':
            print("配置参数获取请参考文档：https://pan.baidu.com/union/doc/ol0rsap9s")
            app_key = input("请输入AppKey:")
            secret_key = input("请输入SecretKey:")
            url = f"https://openapi.baidu.com/oauth/2.0/authorize?response_type=code&client_id={app_key}&redirect_uri=oob&scope=basic,netdisk&force_login=1"
            print(f"请点击下面的链接，打开页面获取授权码：{url}")
            auth_code = input("请输入授权码:")
            refresh_token, access_token = sdk.get_access_token(auth_code, app_key, secret_key)
            account_info = {
                'AppKey': app_key,
                'SecretKey': secret_key,
                'refreshToken': refresh_token,
                'accessToken': access_token
            }
        # 未来可以添加其他网盘的配置逻辑
        # elif pan_type == 'aliyun':
        #     ...
        
        # 保存配置
        if os.path.exists(WangPanCLI.ACCOUNT_CONFIG_FILE):
            with open(WangPanCLI.ACCOUNT_CONFIG_FILE, 'r') as f:
                all_accounts = json.load(f)
        else:
            all_accounts = {}
            
        all_accounts[pan_type] = account_info
        
        with open(WangPanCLI.ACCOUNT_CONFIG_FILE, 'w') as f:
            json.dump(all_accounts, f)
            
        self.account_info[pan_type] = account_info
        print(f"配置完成！配置文件保存在: {WangPanCLI.ACCOUNT_CONFIG_FILE}, 后续会直接读取该配置对网盘文件进行操作。")
    
    def _show_ad(self):
        """显示广告信息"""
        try:
            ad_data = requests.get("https://gitee.com/aierwiki/wangpancli/raw/master/ad_data/latest.json").json()
            ad_data_list = ad_data['ad_data_list']
            # weight就是展现广告的概率
            for ad in ad_data_list:
                if random.random() < ad['weight']:
                    # 使用黄色背景黑色文字显示广告
                    print('\033[43;30m>>> 广告 >>>\033[0m \033[33m{}\033[0m'.format(ad['content']))
                    break
        except Exception as e:
            return
                
    def handle_pan_ls(self, pan_type, path):
        """处理网盘列表查询"""
        if not self.load_config(pan_type):
            print(f"请先配置{pan_type}网盘账号信息: wangpancli config {pan_type}")
            return
            
        sdk = self.get_sdk(pan_type)
        file_list = sdk.get_file_list(path, self.account_info[pan_type]['accessToken'])
        self._show_ad()
        for path, is_dir in file_list:
            if is_dir:
                print('\033[34m{}\033[0m'.format(path))
            else:
                print('\033[32m{}\033[0m'.format(path))
            
    def _parse_pan_path(self, path):
        """
        解析路径字符串，格式为 'pantype:/path'
        如果是网盘路径，返回 (pan_type, real_path)
        否则返回 (None, None)
        """
        for pan_type in self.PAN_SDK_MAP:
            prefix = f"{pan_type}:"
            if path.startswith(prefix):
                return (pan_type, path[len(prefix):])
        return (None, None)
    
    def handle_ls(self, path='./'):
        """
        处理ls命令:
            ls /local/path
            ls baidu:/remote/path
        """
        pan_type, pan_path = self._parse_pan_path(path)
        if pan_type:
            self.handle_pan_ls(pan_type, pan_path)
        else:
            os.system(f"ls {path}")
            
    def handle_download(self, pan_type, pan_src, dest):
        """处理从网盘下载到本地"""
        if not self.load_config(pan_type):
            print(f"请先配置{pan_type}网盘账号信息: wangpancli config {pan_type}")
            return
            
        sdk = self.get_sdk(pan_type)
        logger.debug(f"download {pan_src} to {dest}")
        sdk.download(pan_src, dest, self.account_info[pan_type]['accessToken'])
    
    def handle_upload(self, src, pan_type, pan_dest):
        """处理从本地上传到网盘"""
        if not self.load_config(pan_type):
            print(f"请先配置{pan_type}网盘账号信息: wangpancli config {pan_type}")
            return
            
        sdk = self.get_sdk(pan_type)
        
        if not os.path.exists(src):
            print(f"{src} is not exist!")
            return
            
        if os.path.isfile(src): # 上传单个文件
            pan_dest = os.path.join(pan_dest, os.path.basename(src))
            sdk.upload_file(src, pan_dest, self.account_info[pan_type]['accessToken'])
        else:       # 上传整个文件夹下的所有文件，空文件夹不上传
            last_len = len(os.path.split(src)[-1])
            prefix_len = len(src) - last_len
            # 多于文件夹下存在文件数量过多的场景需要打印进度
            trans_cnt = 0
            for root, dirs, files in os.walk(src):
                for file in files:
                    file_path = os.path.join(root, file)
                    pan_file = os.path.join(pan_dest, file_path[prefix_len:])
                    sdk.upload_file(file_path, pan_file, self.account_info[pan_type]['accessToken'])
                    trans_cnt += 1
                    if trans_cnt >= 100 and trans_cnt % 100 == 0:
                        print(f"transfered {trans_cnt} files ...")
    
    def handle_remote_cp(self, src_pan_type, src_path, dest_pan_type, dest_path):
        """处理网盘之间的文件复制（暂不支持）"""
        print(f"不支持从 {src_pan_type} 网盘到 {dest_pan_type} 网盘的直接复制")

    def handle_cp(self, src, dest):
        """
        处理cp命令:
            cp /local/file baidu:/remote/path
            cp baidu:/remote/file /local/path
            cp /source/file /dest/path
        """
        src_pan_type, src_pan_path = self._parse_pan_path(src)
        dest_pan_type, dest_pan_path = self._parse_pan_path(dest)
        
        if not src_pan_type and not dest_pan_type:
            # 本地到本地复制
            os.system(f"cp {src} {dest}")
        elif src_pan_type and not dest_pan_type:
            # 从网盘下载到本地
            self.handle_download(src_pan_type, src_pan_path, dest)
        elif not src_pan_type and dest_pan_type:
            # 从本地上传到网盘
            self.handle_upload(src, dest_pan_type, dest_pan_path)
        else:
            # 网盘到网盘复制（暂不支持跨网盘复制）
            self.handle_remote_cp(src_pan_type, src_pan_path, dest_pan_type, dest_pan_path)
    
    def handle_mkdir(self, path):
        """
        处理mkdir命令:
            mkdir /local/path
            mkdir baidu:/remote/path
        """
        pan_type, pan_path = self._parse_pan_path(path)
        if not pan_type:
            os.system(f"mkdir {path}")
        else:
            if not self.load_config(pan_type):
                print(f"请先配置{pan_type}网盘账号信息: wangpancli config {pan_type}")
                return
                
            sdk = self.get_sdk(pan_type)
            sdk.make_dir(pan_path, self.account_info[pan_type]['accessToken'])


def main():
    parser = argparse.ArgumentParser(description='WangPanCLI')

    subparsers = parser.add_subparsers(dest='command', help='sub-command help')
    
    # config user info
    config_parser = subparsers.add_parser('config', help="config user info, reference: https://pan.baidu.com/union/doc/ol0rsap9s")
    config_parser.add_argument('pan_type', metavar='pan_type', type=str, nargs='?', default='baidu', 
                               help='pan type to configure, e.g. baidu, aliyun, quark, weiyun')
    
    # ls command
    ls_parser = subparsers.add_parser('ls', help='list files and folders')
    ls_parser.add_argument('path', metavar='path', type=str, nargs='?', default='./', 
                           help='path to list, e.g. /local/path or baidu:/remote/path')

    # cp command
    cp_parser = subparsers.add_parser('cp', help='cp files and folders')
    cp_parser.add_argument('src', metavar='src', type=str, 
                           help='source path, e.g. /local/file or baidu:/remote/file')
    cp_parser.add_argument('dest', metavar='dest', type=str, 
                           help='destination path, e.g. /local/path or baidu:/remote/path')

    # mkdir command
    mkdir_parser = subparsers.add_parser('mkdir', help='make directory')
    mkdir_parser.add_argument('path', metavar='path', type=str, 
                              help='directory path, e.g. /local/path or baidu:/remote/path')

    args = parser.parse_args()
    wangpancli = WangPanCLI()
    
    if args.command == 'config':
        wangpancli.handle_config(args.pan_type)
    elif args.command == 'ls':
        path = args.path
        wangpancli.handle_ls(path)
    elif args.command == 'cp':
        src = args.src
        dest = args.dest
        wangpancli.handle_cp(src, dest)
    elif args.command == 'mkdir':
        path = args.path
        wangpancli.handle_mkdir(path)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
