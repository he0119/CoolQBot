# 问好插件

提供启动问候、每日早安等自动问候功能。

## 功能介绍

- 启动问候：机器人启动时自动发送问候消息
- 每日早安：每天早晨定时发送早安消息，显示距离下个节假日的天数

## 使用方法

### 启动问候

```bash
/hello                       # 查看当前状态
/hello on                    # 开启启动问候
/hello off                   # 关闭启动问候
```

### 每日早安

```bash
/morning                     # 查看当前状态
/morning on                  # 开启每日早安
/morning off                 # 关闭每日早安
```

## 配置说明

在配置文件中可以设置早安发送时间：

```env
MORNING_TIME=07:30
```

所有命令需要**管理员权限**才能开启/关闭问候功能，普通用户只能查看当前状态。
