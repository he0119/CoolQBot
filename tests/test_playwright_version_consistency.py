"""检查 Python 的 playwright 包和浏览器镜像版本是否完全一致。

机器人不自己装浏览器，而是连到一个跑着浏览器的容器上。Playwright 要求两边版本
**完全相同**，差一点都不行——服务端会直接回 428 拒绝连接：

    Playwright version mismatch:
    - server version: v1.63
    - client version: v1.64

而渲染失败不会报错，只会静默退回纯文本（见 handler.try_render_markdown），
所以线上表现只是"图片没了"，很难发现。

这两个版本分别写在不同的文件里，很容易忘记同步。之前就出过一次：Python 包升到
1.64.0，镜像还停在 1.61.1，图片全挂。

注意 htmlrender 自己也有一层版本检查，但它比 Playwright 宽松得多（次版本差 1
只告警），而且远程版本探不到时它会直接放行。真正决定能不能连上的是 Playwright
自己，所以这里必须按"完全相等"来测。
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_VERSION_RE = r"(\d+\.\d+\.\d+)"


def _read_python_playwright_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(rf'"playwright=={_VERSION_RE}"', text)
    assert match, "pyproject.toml 中未找到 playwright==x.y.z 形式的固定版本"
    return match.group(1)


def _read_compose_image_version() -> str:
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    match = re.search(rf"image:\s*mcr\.microsoft\.com/playwright:v{_VERSION_RE}", text)
    assert match, "docker-compose.yml 中未找到官方 playwright 镜像版本"
    return match.group(1)


def _read_ci_image_version() -> str:
    text = (ROOT / ".github" / "workflows" / "main.yml").read_text(encoding="utf-8")
    match = re.search(rf"mcr\.microsoft\.com/playwright:v{_VERSION_RE}", text)
    assert match, "CI workflow 中未找到官方 playwright 镜像版本"
    return match.group(1)


def _read_compose_server_command_version() -> str:
    """compose 里 run-server 用的 playwright 版本，也要和镜像 tag 一致。"""
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    match = re.search(rf"npx -y playwright@{_VERSION_RE} run-server", text)
    assert match, "docker-compose.yml 中未找到 run-server 的 playwright 版本"
    return match.group(1)


def test_python_and_compose_browser_versions_match_exactly():
    """pyproject.toml 的 playwright 要和 docker-compose.yml 的镜像版本完全一致。"""
    local = _read_python_playwright_version()
    remote = _read_compose_image_version()

    assert local == remote, (
        f"playwright 版本不一致：pyproject.toml 是 {local}，"
        f"docker-compose.yml 的镜像是 {remote}。"
        "Playwright 要求两边完全相同，否则连不上浏览器，"
        "所有 Markdown 转图片都会失败并静默退回文字。"
    )


def test_python_and_ci_browser_versions_match_exactly():
    """CI 用的镜像版本也要和 Python 包完全一致，否则 CI 跟线上不是一回事。"""
    local = _read_python_playwright_version()
    remote = _read_ci_image_version()

    assert local == remote, f"CI 用的浏览器镜像 {remote} 与 playwright {local} 不一致。"


def test_compose_and_ci_use_same_browser_image():
    """本地跑的镜像和 CI 跑的必须是同一个，否则本地测过不代表 CI 能过。"""
    assert _read_compose_image_version() == _read_ci_image_version(), (
        "docker-compose.yml 和 CI workflow 里的浏览器镜像版本不一致。"
    )


def test_run_server_command_matches_image_tag():
    """镜像 tag 和 run-server 的版本也要一致，否则容器里跑的是另一个版本。"""
    assert _read_compose_server_command_version() == _read_compose_image_version(), (
        "docker-compose.yml 里 run-server 的 playwright 版本和镜像 tag 不一致。"
    )
