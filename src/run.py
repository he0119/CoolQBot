from coolqbot import nonebot

if __name__ == '__main__':
    nonebot.load_plugins(nonebot.get_bot().config.PLUGINS_DIR_PATH, 'plugins')
    nonebot.run()
