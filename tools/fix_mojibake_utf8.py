"""
Sửa lỗi mojibake tiếng Việt (UTF-8 bị decode nhầm Latin-1) và chuẩn hóa file về UTF-8.

Ý tưởng:
- Nhiều file bị lưu/đọc sai kiểu: bytes UTF-8 -> decode nhầm Latin-1 -> lưu lại.
- Có thể "giải mã ngược" bằng: seg.encode('latin1').decode('utf-8')

Script này:
- Quét các file văn bản phổ biến trong repo (py/html/js/css/json/csv/md)
- Chỉ sửa những đoạn (segment) nằm trong dải Latin-1 và có dấu hiệu mojibake
- Ghi lại file dưới dạng UTF-8 (không BOM), giữ kiểu xuống dòng gốc (CRLF/LF)
"""

from __future__ import annotations

import re
from pathlib import Path


TEXT_EXTS = {".py", ".html", ".js", ".css", ".json", ".csv", ".md"}
EXCLUDE_PARTS = {".git", "__pycache__", ".venv", "venv", "node_modules"}

# Các dấu hiệu thường gặp trong mojibake tiếng Việt.
# Dùng Unicode escapes để tránh phụ thuộc môi trường hiển thị.
SUSP_MARKERS = (
    "\u00c3",          # U+00C3
    "\u00e1\u00bb",    # U+00E1 U+00BB
    "\u00e1\u00ba",    # U+00E1 U+00BA
    "\u00c4\u2018",    # U+00C4 U+2018
    "\u00c6\u00b0",    # U+00C6 U+00B0
)

# Các đoạn chỉ chứa ký tự Latin-1 (<= 0xFF). Nếu có mojibake, thường nằm trong nhóm này.
LATIN1_SEGMENT_RE = re.compile(r"[\u0000-\u00FF]{2,}")


def suspicious_count(s: str) -> int:
    return sum(s.count(m) for m in SUSP_MARKERS)


def fix_segment(seg: str) -> str:
    if not any(m in seg for m in SUSP_MARKERS):
        return seg

    try:
        decoded = seg.encode("latin1").decode("utf-8")
    except Exception:
        return seg

    # Chỉ nhận nếu giảm dấu hiệu mojibake rõ rệt
    if suspicious_count(decoded) >= suspicious_count(seg):
        return seg

    return decoded


def fix_text(text: str) -> str:
    return LATIN1_SEGMENT_RE.sub(lambda m: fix_segment(m.group(0)), text)


def detect_newline_style(raw: bytes) -> str:
    # Ưu tiên giữ CRLF nếu file gốc dùng CRLF nhiều
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n")
    return "\r\n" if crlf and crlf >= (lf // 2) else "\n"


def iter_candidate_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in TEXT_EXTS:
            continue
        if any(part in EXCLUDE_PARTS for part in p.parts):
            continue
        files.append(p)
    return files


def main() -> int:
    root = Path(".")
    changed: list[Path] = []

    for path in iter_candidate_files(root):
        raw = path.read_bytes()
        newline = detect_newline_style(raw)

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback: vẫn cố đọc để fix, sau đó ghi UTF-8 chuẩn
            text = raw.decode("utf-8", errors="replace")

        if suspicious_count(text) == 0:
            continue

        fixed = fix_text(text)
        if fixed == text:
            continue

        # Giữ kiểu xuống dòng gốc
        if newline == "\r\n":
            fixed_out = fixed.replace("\n", "\r\n")
        else:
            fixed_out = fixed

        path.write_bytes(fixed_out.encode("utf-8"))
        changed.append(path)

    print(f"Changed {len(changed)} file(s).")
    for p in changed:
        print("-", p.as_posix())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
