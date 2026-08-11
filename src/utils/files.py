"""文件操作工具。"""

import os
import tempfile
from pathlib import Path


def write_bytes_atomic(file: Path, content: bytes) -> None:
    """在同一目录写入临时文件，再原子替换目标文件。"""
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=file.parent, prefix=f".{file.name}.", delete=False) as f:
            temporary_path = Path(f.name)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        temporary_path.replace(file)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
