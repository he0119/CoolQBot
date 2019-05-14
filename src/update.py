""" 升级脚本

升级 0.6.2 及以前的版本的 recorder 数据。
"""
import pickle
from pathlib import Path
from datetime import datetime

home = Path()


def save_pkl(data, filename):
    with open(str(filename), 'wb') as f:
        pickle.dump(data, f)


def load_pkl(filename):
    with open(str(filename), 'rb') as f:
        data = pickle.load(f)
    return data


for f in home.iterdir():
    if f.suffix == '.pkl':
        data = load_pkl(f)
        data['msg_send_time'] = []
        tmp = data['repeat_list']
        data['repeat_list'] = {}
        data['repeat_list'][0] = tmp
        tmp = data['msg_number_list']
        data['msg_number_list'] = {}
        data['msg_number_list'][0] = tmp
        save_pkl(data, f)
        print(data)
