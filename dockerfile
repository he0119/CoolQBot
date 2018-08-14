FROM richardchien/cqhttp:latest
ENV CQHTTP_POST_URL=http://127.0.0.1:8080 \
    CQHTTP_SERVE_DATA_FILES=yes
COPY src /home/user/coolqbot
RUN apt-get update; \
    apt-get install -y git build-essential libreadline-dev libsqlite3-dev libbz2-dev libssl-dev zlib1g-dev; \
    git clone https://github.com/pyenv/pyenv.git ~/.pyenv; \
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc; \
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc; \
    echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bashrc; \
    exec $SHELL; \
    pyenv install 3.6.6; \
    cd /home/user/coolqbot && pyenv local 3.6.6 && python run.py
