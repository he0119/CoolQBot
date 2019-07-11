""" 升级脚本

升级 0.7.0-0.8.1 版本的 recorder 数据。
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

group_id = int(input('请输入群号：'))
for f in home.iterdir():
    if f.suffix == '.pkl':
        data = load_pkl(f)

        # 升级 last_message_on
        tmp = data['last_message_on']
        data['last_message_on'] = {}
        data['last_message_on'][group_id] = tmp

        # 升级 msg_send_time
        data['msg_send_time'] = {}
        data['msg_send_time'][group_id] = []

        # 升级 repeat_list
        tmp = data['repeat_list']
        data['repeat_list'] = {}
        data['repeat_list'][group_id] = tmp

        # 升级 msg_number_list
        tmp = data['msg_number_list']
        data['msg_number_list'] = {}
        data['msg_number_list'][group_id] = tmp
        save_pkl(data, f)
        print(data)
