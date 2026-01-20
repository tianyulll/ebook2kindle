pyinstaller --onefile -n ebook2kindle --add-binary '/Users/tylu/tool/kaf/kaf-cli:.' \
--add-binary "/Users/tylu/miniforge3/envs/ebook/bin/ebook-converter:." \
--additional-hooks-dir=. --windowed --clean main.py

