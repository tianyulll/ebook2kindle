pyinstaller --onefile -n ebook2kindle -y \
--add-binary "/Users/tylu/miniforge3/envs/ebook/bin/ebook-converter:." \
--additional-hooks-dir=. --windowed --clean main.py

