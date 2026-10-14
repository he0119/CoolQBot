"""确保升级 htmlrender 时不会把 bison 弄坏。

bison 0.9.14 用的是 htmlrender 0.7 的 API：

    from nonebot_plugin_htmlrender import md_to_pic, text_to_pic, get_new_page
    from nonebot_plugin_htmlrender.browser import get_new_page, get_browser

htmlrender 0.8 把这几个全删了（改成了 render_text / render_markdown /
Renderer 那一套，也没留别名），而 bison 上游至今没有适配。结果就是 bison
的浏览器 theme（arknights / ceobecanteen / ht2i）和 bilibili 抓取会在渲染时
直接抛 ModuleNotFoundError。

更麻烦的是 bison 的 theme 兜底机制接不住这个异常——它只捕获 ThemeRenderError，
而 ModuleNotFoundError 不是它的子类，所以会直接往上抛，整条推送失败，
不会降级成文字。

所以这里把"bison 需要的 API 必须存在"固定成测试，免得 Renovate 又悄悄跨大版本。
bison 适配之后，这个文件可以整个删掉。

实现说明：这里用 ast 静态解析 __init__.py 的 __all__，而不是真的 import。
因为 htmlrender 在 import 时会调用 localstore 的 get_plugin_cache_dir()，
那要求调用方是插件模块；在测试里 import 会报 "Cannot detect caller plugin"，
而且会污染共享的 driver 状态，导致后面的测试挂掉。
静态检查同样能发现"API 被删了"，而且没有副作用。

另外，bison 是在函数内部 import 的，所以 0.8 那种"删了 API"不会在启动时报错，
只有渲染时才炸——静态检查正好能提前拦住。
"""

import ast
from pathlib import Path

import pytest

# bison 实际用到的地方，改 bison 版本时记得回来核对
BISON_REQUIRED_ATTRS = {
    # ht2i theme / utils/image.py 图文渲染 / 网页截图 / ceobecanteen / arknights
    "nonebot_plugin_htmlrender": [
        "md_to_pic",
        "text_to_pic",
        "get_new_page",
        "template_to_pic",
    ],
    # bilibili 抓取会 import 这个模块
    "nonebot_plugin_htmlrender.browser": ["get_browser", "get_new_page"],
}

# 我们自己（llm 插件）用的，也一并守住
OWN_REQUIRED_ATTRS = {
    "nonebot_plugin_htmlrender": ["render_markdown"],
}

REQUIRED_ATTRS = {**BISON_REQUIRED_ATTRS, **OWN_REQUIRED_ATTRS}


def _htmlrender_version() -> str:
    from importlib.metadata import version

    return version("nonebot-plugin-htmlrender")


def _major_minor() -> tuple[int, int]:
    parts = _htmlrender_version().split(".")
    return int(parts[0]), int(parts[1])


def _site_packages() -> Path:
    """htmlrender 装在哪。

    从 sys.modules 里取已经加载过的包，不要在这里 import：
    NoneBot 的插件系统靠调用栈判断「谁在 import 我」，在测试函数里 import
    会报 "Cannot detect caller plugin"。conftest 的 after_nonebot_init 已经
    加载过 htmlrender，所以 sys.modules 里一定有。
    """
    import sys

    module = sys.modules.get("nonebot_plugin_htmlrender")
    if module is not None and getattr(module, "__file__", None):
        return Path(module.__file__).parent

    # 兜底：直接按 site-packages 目录找，不触发导入
    import site
    import sysconfig

    for base in [*site.getsitepackages(), sysconfig.get_paths()["purelib"]]:
        candidate = Path(base) / "nonebot_plugin_htmlrender" / "__init__.py"
        if candidate.is_file():
            return candidate.parent
    raise AssertionError("找不到 nonebot_plugin_htmlrender 的安装位置")


def _module_path(module_name: str) -> Path | None:
    """由模块名推出文件路径，不用 importlib.find_spec。

    find_spec 会顺带 import 父包 __init__，在 NoneBot 没初始化时会炸；
    这里直接按文件系统拼路径，避免副作用。模块不存在时返回 None。
    """
    pkg_root = _site_packages()
    parts = module_name.split(".")
    assert parts[0] == "nonebot_plugin_htmlrender", module_name

    rel = parts[1:]
    if not rel:  # 包本身
        return pkg_root / "__init__.py"

    as_file = pkg_root.joinpath(*rel).with_suffix(".py")
    if as_file.is_file():
        return as_file

    as_pkg = pkg_root.joinpath(*rel) / "__init__.py"
    return as_pkg if as_pkg.is_file() else None


def _exported_names(module_name: str) -> set[str] | None:
    """静态解析模块里定义/导出的顶层名字；模块不存在时返回 None。"""
    path = _module_path(module_name)
    if path is None:
        return None

    tree = ast.parse(path.read_text(encoding="utf-8"))

    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)

    # __all__ 里列出的名字也算显式导出
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, ast.List | ast.Tuple):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                names.add(elt.value)

    return names


def test_htmlrender_is_pinned_below_08():
    """htmlrender 必须锁在 0.7.x，否则 bison 会坏。"""
    assert _major_minor() < (0, 8), (
        f"装到了 htmlrender {_htmlrender_version()}，但 bison 还需要 0.7 的 API。"
        "请把 pyproject.toml 里的上界恢复成 <0.8.0，"
        "或等 bison 上游完成适配后再放开这个测试。"
    )


@pytest.mark.parametrize(
    ("module_name", "attr"),
    [(m, a) for m, attrs in REQUIRED_ATTRS.items() for a in attrs],
)
def test_required_api_exists(module_name: str, attr: str):
    """bison 和我们自己用到的 htmlrender API 都必须存在。"""
    exported = _exported_names(module_name)
    assert exported is not None, (
        f"htmlrender 里没有 {module_name} 这个模块了。"
        "bison（或本项目）依赖它，说明 htmlrender 大版本升级把这个模块删掉了。"
    )
    assert attr in exported, (
        f"{module_name} 里找不到 {attr}。bison（或本项目）依赖它，说明 htmlrender 大版本升级删掉了这个 API。"
    )
