import argparse
import requests
import json
import os
import random
import hashlib
from urllib.parse import urlencode
# from wangpancli.baidu_pan_sdk import BaiduPanSDK
from .baidu_pan_sdk import BaiduPanSDK
from loguru import logger
# logger.remove(0)


class WangPanCLI():
    ACCOUNT_CONFIG_FILE = os.path.expanduser('~/.cache/wangpancli/account_info.json')
    
    def __init__(self):
        self.account_info = {}
        self.sdk = BaiduPanSDK()
        if not os.path.exists(os.path.dirname(WangPanCLI.ACCOUNT_CONFIG_FILE)):
            os.makedirs(os.path.dirname(WangPanCLI.ACCOUNT_CONFIG_FILE))
    
    def load_config(self):
        if not os.path.exists(WangPanCLI.ACCOUNT_CONFIG_FILE):
            logger.debug(f"{WangPanCLI.ACCOUNT_CONFIG_FILE} not exist!")
            return False
        account_info = {}
        with open(WangPanCLI.ACCOUNT_CONFIG_FILE, 'r') as f:
            account_info =  json.load(f)
        required_keys = ['AppKey', 'SecretKey', 'refreshToken', 'accessToken']
        for key in required_keys:
            if key not in account_info:
                logger.debug(f"{key} not in account_info")
                return False
        self.account_info = account_info
        return True

    def handle_config(self):
        print("配置参数获取请参考文档：https://pan.baidu.com/union/doc/ol0rsap9s")
        app_key = input("请输入AppKey:")
        secret_key = input("请输入SecretKey:")
        url = f"https://openapi.baidu.com/oauth/2.0/authorize?response_type=code&client_id={app_key}&redirect_uri=oob&scope=basic,netdisk&force_login=1"
        print(f"请点击下面的链接，打开页面获取授权码：{url}")
        auth_code = input("请输入授权码:")
        refresh_token, access_token = self.sdk.get_access_token(auth_code, app_key, secret_key)
        account_info = {
            'AppKey': app_key,
            'SecretKey': secret_key,
            'refreshToken': refresh_token,
            'accessToken': access_token
        }
        with open(WangPanCLI.ACCOUNT_CONFIG_FILE, 'w') as f:
            json.dump(account_info, f)
        self.account_info = account_info
        print(f"配置完成！配置文件保存在: {WangPanCLI.ACCOUNT_CONFIG_FILE}, 后续会直接读取该配置对网盘文件进行操作。")
    
    def _show_ad():
        """
        显示广告信息
        获取广告数据
        {
            "ad_data_list": [
                {
                    "id": "001",
                    "weight": 1.0,
                    "content": "[AD] 广告位招商，欢迎合作，请联系微信：AAAAA-haha"
                }
            ]
        }
        """
        try:
            ad_data = requests.get("https://gitee.com/aierwiki/wangpancli/raw/master/ad_data/latest.json").json()
            ad_data_list = ad_data['ad_data_list']
            # weight就是展现广告的概率
            for ad in ad_data_list:
                if random.random() < ad['weight']:
                    print(ad['content'])
                    break
        except Exception as e:
            return
                
    def handle_pan_ls(self, path):
        file_list = self.sdk.get_file_list(path, self.account_info['accessToken'])
        self._show_ad()
        for path, is_dir in file_list:
            if is_dir:
                print('\033[34m{}\033[0m'.format(path))
            else:
                print('\033[32m{}\033[0m'.format(path))
            
    def _parse_pan_path(self, path):
        """解析路径字符串，如果存在'wangpan:'则认为path将'wangpan:'去掉就是网盘的路径并返回，否则path按照本地路径处理，返回None。
        """
        pan_path = None
        if path[:7] == 'wangpan:':
            pan_path = path[7:]
        return pan_path
    
    def handle_ls(self, path='./'):
        """
        ls命令场景如下：
            ls /local/path
            ls /local/path/file
            ls wangpan:/local/path
            ls wangpan:/local/path/file
        """
        pan_path = self._parse_pan_path(path)
        if pan_path is not None:
            self.handle_pan_ls(pan_path)
        else:
            os.system(f"ls {path}") 
            
    def handle_download(self, pan_src, dest):
        logger.debug(f"download {pan_src} to {dest}")
        self.sdk.download(pan_src, dest, self.account_info['accessToken'])
    
    def handle_upload(self, src, pan_dest):
        if not os.path.exists(src):
            print(f"{src} is not exist!")
            return
        if os.path.isfile(src): # 上传单个文件
            pan_dest = os.path.join(pan_dest, os.path.basename(src))
            self.sdk.upload_file(src, pan_dest, self.account_info['accessToken'])
        else:       # 上传整个文件夹下的所有文件，空文件夹不上传
            last_len = len(os.path.split(src)[-1])
            prefix_len = len(src) - last_len
            # 多于文件夹下存在文件数量过多的场景需要打印进度
            trans_cnt = 0
            for root, dirs, files in os.walk(src):
                for file in files:
                    file_path = os.path.join(root, file)
                    pan_file = os.path.join(pan_dest, file_path[prefix_len:])
                    self.sdk.upload_file(file_path, pan_file, self.account_info['accessToken'])
                    trans_cnt += 1
                    if trans_cnt >= 100 and trans_cnt % 100 == 0:
                        print(f"transfered {trans_cnt} files ...")
            
    
    def handle_remote_cp(self, pan_src, pan_dest):
        print("not yet supported")

    def handle_cp(self, src, dest):
        pan_src = self._parse_pan_path(src)
        pan_dest = self._parse_pan_path(dest)
        if pan_src is None and pan_dest is None:
            os.system(f"cp {src} {dest}")
        elif pan_src is not None and pan_dest is None:
            self.handle_download(pan_src, dest)
        elif pan_src is None and pan_dest is not None:
            self.handle_upload(src, pan_dest)
        else:
            self.handle_remote_cp(pan_src, pan_dest)
    
    def handle_mkdir(self, path):
        pan_path = self._parse_pan_path(path)
        if pan_path is None:
            os.system(f"mkdir {path}")
        else:
            self.sdk.make_dir(pan_path, self.account_info['accessToken'])



def main():
    parser = argparse.ArgumentParser(description='WangPanCLI')

    subparsers = parser.add_subparsers(dest='command', help='sub-command help')
    
    # config user info
    config_parser = subparsers.add_parser('config', help="config user info, reference: https://pan.baidu.com/union/doc/ol0rsap9s")
    
    # ls command
    ls_parser = subparsers.add_parser('ls', help='list files and folders')
    ls_parser.add_argument('path', metavar='path', type=str, nargs='?', default='./', help='path to list')

    # cp command
    cp_parser = subparsers.add_parser('cp', help='cp files and folders')
    cp_parser.add_argument('src', metavar='src', type=str, help='source path')
    cp_parser.add_argument('dest', metavar='dest', type=str, help='destination path')

    # mkdir command
    mkdir_parser = subparsers.add_parser('mkdir', help='make directory')
    mkdir_parser.add_argument('path', metavar='path', type=str, help='directory path')

    args = parser.parse_args()
    wangpancli = WangPanCLI()
    
    if args.command == 'config':
        wangpancli.handle_config()
    elif args.command in ('ls', 'cp', 'mkdir'):
        config_ok = wangpancli.load_config()
        if not config_ok:
            print("工具使用前需要先配置账号. 请执行后面的命令配置网盘账号信息：wangpancli config")
            return
        
        if args.command == 'ls':
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
