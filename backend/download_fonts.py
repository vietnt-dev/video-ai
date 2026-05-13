"""
Script tải font Roboto (hỗ trợ tiếng Việt đầy đủ) về thư mục assets/fonts.
Chạy một lần trước khi start server: python download_fonts.py
"""
import urllib.request
import zipfile
import os
from pathlib import Path

FONT_DIR = Path("./assets/fonts")
FONT_DIR.mkdir(parents=True, exist_ok=True)

# Google Fonts - Roboto (hỗ trợ Latin Extended / tiếng Việt)
FONTS = {
    "Roboto-Bold.ttf": "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Bold.ttf",
    "Roboto-Black.ttf": "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Black.ttf",
}

print("📥 Đang tải font Roboto (hỗ trợ tiếng Việt)...")

for filename, url in FONTS.items():
    dest = FONT_DIR / filename
    if dest.exists():
        print(f"  ✅ {filename} đã tồn tại, bỏ qua")
        continue

    print(f"  ⬇️  Đang tải {filename}...")
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"  ✅ {filename} đã tải xong")
    except Exception as e:
        print(f"  ❌ Lỗi tải {filename}: {e}")
        print(f"     Tải thủ công tại: {url}")

print("\n✅ Font setup hoàn tất!")
print(f"   Fonts được lưu tại: {FONT_DIR.absolute()}")
