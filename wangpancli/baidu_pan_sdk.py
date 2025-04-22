import requests
import json
import os
import math
from time import sleep
import hashlib
from urllib.parse import urlencode
from rich.progress import track
from loguru import logger
logger.remove(0)


class BaiduPanSDK:
    # access_token获取地址
    ACCESS_TOKEN_API = 'https://openapi.baidu.com/oauth/2.0/token'
    # 预创建文件接口
    PRECREATE_API = 'https://pan.baidu.com/rest/2.0/xpan/file?'
    # 分片上传api
    UPLOAD_API = 'https://d.pcs.baidu.com/rest/2.0/pcs/superfile2?'
    # 创建文件api
    CREATE_API = 'https://pan.baidu.com/rest/2.0/xpan/file?'
    # 获取文件列表
    FILE_MANAGE_API = 'https://pan.baidu.com/rest/2.0/xpan/file?'
    # 查询文件信息
    FILE_INFO_API = "http://pan.baidu.com/rest/2.0/xpan/multimedia?"
    
    ERROR_INFO = {-7: '文件或目录名错误或无权访问', -9: '文件或目录不存在', -8: '文件或目录已存在', -10: '云端容量已满',
                  42211: '图片详细信息查询失败', 42212: '共享目录文件上传者信息查询失败，可重试', 42213: '共享目录鉴权失败', 42214: '文件基础信息查询失败'}
    
    def __init__(self) -> None:
        self.account_info = {}
    
    # 根据授权码获取token
    def get_access_token(self, code, app_key, secret_key):
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': app_key,
            'client_secret': secret_key,
            'redirect_uri': 'oob'
        }
        res = requests.post(BaiduPanSDK.ACCESS_TOKEN_API, data=data)
        json_resp = json.loads(res.content)
        refresh_token = json_resp['refresh_token']
        access_token = json_resp['access_token']
        return refresh_token, access_token
    
    # 创建文件
    def create(self, remote_path, size, uploadid, block_list, access_token):
        params = {
            'method': 'create',
            'access_token': access_token,
        }
        api = BaiduPanSDK.CREATE_API + urlencode(params)
        data = {
            'path': remote_path,
            'size': size,
            'isdir': 0,
            'uploadid': uploadid,
            'block_list': block_list
        }
        response = requests.post(api, data=data)

    # 分片上传
    def upload(self, remote_path, uploadid, partseq, file_path, access_token):
        
        with open(file_path, "rb") as f:
            size = os.path.getsize(file_path)
            buffer_size = 4 * 1024 * 1024
            buffer_cnt = math.ceil(size / buffer_size)
            for seq in track(range(buffer_cnt), description="上传中..."):
                buffer = f.read(buffer_size)
                if not buffer:
                    break
                files = [
                    ('file', buffer)
                ]
                params = {
                    'method': 'upload',
                    'access_token': access_token,
                    'path': remote_path,
                    'type': 'tmpfile',
                    'uploadid': uploadid,
                    'partseq': seq
                }
                api = BaiduPanSDK.UPLOAD_API + urlencode(params)
                res = requests.post(api, files=files)
                # 如果失败了则重试10次
                if res.status_code != 200:
                    for _ in range(10):
                        sleep(2)
                        res = requests.post(api, files=files)
                        if res.status_code != 200:
                            break
                if res.status_code != 200:      
                    print(BaiduPanSDK.ERROR_INFO.get(res.status_code, '未知错误'))
                    return False
        
        return True
        
    def precreate(self, local_file_path, remote_file_path, access_token):  
        block_list = []
        with open(local_file_path, 'rb') as f:
            size = os.path.getsize(local_file_path)
            buffer_size = 4 * 1024 * 1024
            buffer_cnt = math.ceil(size / buffer_size)
            for seq in track(range(buffer_cnt), description="文件读取中..."):
                buffer = f.read(buffer_size)
                if not buffer:
                    break
                buffer_md5 = hashlib.md5(buffer).hexdigest()
                block_list.append(buffer_md5)   
        block_list = json.dumps(block_list)
        params = {
            'method': 'precreate',
            'access_token': access_token,
        }
        data = {
            'path': remote_file_path,
            'size': size,
            'isdir': 0,
            'autoinit': 1,
            'block_list': block_list
        }
        api = BaiduPanSDK.PRECREATE_API + urlencode(params)
        res = requests.post(api, data=data)
        if res.status_code != 200:
            print(BaiduPanSDK.ERROR_INFO.get(res.status_code, '未知错误'))
            return None, None, None
        result = json.loads(res.content)
        return result['uploadid'], size, block_list
        
    def upload_file(self, local_file_path, remote_file_path, access_token):
        logger.debug(f"upload {local_file_path} to {remote_file_path}")
        # 1. 预上传
        uploadid, size, block_list = self.precreate(local_file_path, remote_file_path, access_token)
        if uploadid is None:
            return False
        # 2. 分片上传（文件切片这里没有做，超级会员单文件最大20G）
        ret = self.upload(remote_file_path, uploadid, 0, local_file_path, access_token)
        if not ret:
            return False
        # 3. 创建文件
        self.create(remote_file_path, size, uploadid, block_list, access_token)
        return True
    
    def get_file_list(self, dir, access_token):
        params = {
            'method': 'list',
            'access_token': access_token,
            'dir': dir,
            'showempty': 1
        }
        data = {}
        api = BaiduPanSDK.FILE_MANAGE_API + urlencode(params)
        logger.debug(f"api={api}")
        res = requests.get(api, data=data).json()
        if res['errno'] != 0:
            print(BaiduPanSDK.ERROR_INFO.get(res['errno'], '未知错误'))
            return []
        logger.debug(f"res = {res}")
        file_list = res['list']
        file_list = [(item['path'], item['isdir']) for item in file_list]
        return file_list
    
    def make_dir(self, dir, access_token):
        params = {
            'method': 'create',
            'access_token': access_token,
        }
        data = {
            'path': dir,
            'rtype': '0',
            'isdir': '1'
        }
        api = BaiduPanSDK.FILE_MANAGE_API + urlencode(params)
        logger.debug(f"api={api}")
        res = requests.post(api, data=data).json()
        logger.debug(f"res={res}")
        if res['errno'] != 0:
            print(BaiduPanSDK.ERROR_INFO.get(res['errno'], '未知错误'))
            return False
        return True
    
    def _get_child_dict(self, dir, access_token):
        params = {
            'method': 'list',
            'access_token': access_token,
            'dir': dir,
            'showempty': 1
        }
        data = {}
        api = BaiduPanSDK.FILE_MANAGE_API + urlencode(params)
        logger.debug(f"api={api}")
        res = requests.get(api, data=data).json()
        if res['errno'] != 0:
            print(BaiduPanSDK.ERROR_INFO.get(res['errno'], '未知错误'))
            return []
        child_list = res['list']
        child_list = {item['path'] : {'isdir': item['isdir'], 'fs_id': item['fs_id'], 'server_filename': item['server_filename'], 'path': item['path']} for item in child_list}
        return child_list
    
    def download_file(self, fs_id, filename, dest, access_token):
        params = {
            'method': 'filemetas',
            'access_token': access_token,
            'fsids': [fs_id,],
            'dlink': 1
        }
        data = {}
        api = BaiduPanSDK.FILE_INFO_API + urlencode(params)
        logger.debug(f"api={api}")
        res = requests.get(api, data=data).json()
        if res['errno'] != 0:
            print(BaiduPanSDK.ERROR_INFO.get(res['errno'], '未知错误'))
            return False
        result_list = res['list']
        dlink_list = [result['dlink'] for result in result_list]
        dlink = dlink_list[0]
        download_url = dlink + f'&access_token={access_token}'
        cmd = f"wget --header='User-Agent: pan.baidu.com' '{download_url}' -O {os.path.join(dest, filename)}"
        logger.debug(f"cmd = {cmd}")
        print(f"download {filename} complete !")
        os.system(cmd)
        
    
    def download(self, pan_path, dest, access_token):
        logger.debug(f"download {pan_path} to {dest}")
        if pan_path[-1] == '/':
            child_dict = self._get_child_dict(pan_path, access_token)
            for path, child in child_dict.items():
                if child['isdir'] == 1:
                    sub_dir = os.path.join(dest, child['server_filename'])
                    os.system(f"mkdir {sub_dir}")
                    self.download(path + "/", sub_dir, access_token)
                else:
                    self.download_file(child['fs_id'], child['server_filename'], dest, access_token)
        else:
            parent_dir = os.path.join(*os.path.split(pan_path)[:-1])
            child_dict = self._get_child_dict(parent_dir, access_token)
            if pan_path not in child_dict:
                logger.error(f"{pan_path} not in {child_dict}")
                return
            child = child_dict[pan_path]
            if child['isdir'] == 0:
                self.download_file(child['fs_id'], child['server_filename'], dest, access_token)
            else:
                sub_dir = os.path.join(dest, child['server_filename'])
                os.system(f"mkdir {sub_dir}")
                self.download(pan_path + "/", sub_dir, access_token)
                
       