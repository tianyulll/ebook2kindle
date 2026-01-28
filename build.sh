pyinstaller --onedir -n ebook2kindle -y \
--additional-hooks-dir=. --windowed \
--add-binary "/Users/tylu/miniforge3/envs/ebook/bin/ebook-converter:." \
--clean main.py


pyinstaller --onedir -n ebook2kindle -y \
--additional-hooks-dir=. --windowed \
--clean main.py

pyinstaller --onefile -n ebook2kindle -y \
--additional-hooks-dir=. --windowed \
--clean main.py