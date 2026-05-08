
conda activate ebook

pyinstaller --onedir -n ebook2kindle -y \
--additional-hooks-dir=. --windowed \
--icon img/ebook.icns \
--clean main.py


ditto -c -k --sequesterRsrc --keepParent \
  ebook2kindle.app ebook2kindle.zip