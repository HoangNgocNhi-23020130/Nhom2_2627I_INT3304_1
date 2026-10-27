import os
import shutil
import subprocess
import sys
from pathlib import Path
from app.config import BOTS_DIR, ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES


class CompilerError(Exception):
    pass


def compile_cpp(source_path: Path | str) -> str:
    src = Path(source_path).resolve()
    if not src.exists():
        raise CompilerError(f"Không tìm thấy file nguồn: {src}")

    bin_suffix = ".exe" if sys.platform.startswith("win") else ""
    binary_dest = src.parent / f"{src.stem}_bin{bin_suffix}"
    compiler = shutil.which("g++") or shutil.which("clang++")

    if not compiler:
        raise CompilerError("Máy chủ thiếu trình biên dịch g++ hoặc clang++.")

    compile_cmd = [compiler, "-O2", "-std=c++17", str(src), "-o", str(binary_dest)]
    result = subprocess.run(compile_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise CompilerError(f"Biên dịch C++ thất bại:\n{result.stderr}")

    try:
        os.chmod(binary_dest, 0o755)
    except Exception:
        pass

    return str(binary_dest)


def prepare_bot(filename: str, file_content: bytes) -> tuple[str, str, str | None]:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise CompilerError(f"Định dạng {ext} không hỗ trợ. Chỉ chấp nhận .py, .cpp, .js")

    if len(file_content) > MAX_UPLOAD_BYTES:
        raise CompilerError("Dung lượng file tối đa là 2MB.")

    BOTS_DIR.mkdir(parents=True, exist_ok=True)
    base_name = Path(filename).stem
    dest_source = BOTS_DIR / filename

    with open(dest_source, "wb") as f:
        f.write(file_content)

    language = "python"
    binary_path = None

    if ext == ".py":
        language = "python"
    elif ext == ".js":
        language = "javascript"
    elif ext == ".cpp":
        language = "cpp"
        try:
            binary_path = compile_cpp(dest_source)
        except CompilerError as e:
            if dest_source.exists():
                dest_source.unlink()
            raise e

    return base_name, language, binary_path