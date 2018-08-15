docker pull he0119/coolqbot:latest
mkdir coolq  # 用于存储酷 Q 的程序文件
docker run -ti --rm --name cqhttp-test \
  -v $(pwd)/coolq:/home/user/coolq \  # 将宿主目录挂载到容器内用于持久化酷 Q 的程序文件
  -p 9000:9000 \  # noVNC 端口，用于从浏览器控制酷 Q
  -e COOLQ_ACCOUNT=2062765419 \ # 要登录的 QQ 账号，可选但建议填
  -e VNC_PASSWD=12345687 \ # noVNC 的密码（官方说不能超过 8 个字符，但实测可以超过）
  he0119/coolqbot:latest
