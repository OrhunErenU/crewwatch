ls ~/esaenv/bin | head; ~/esaenv/bin/python -c "import numpy, scipy; print(numpy.__version__, scipy.__version__)" 2>&1; python3 -c "import numpy; print('sys numpy', numpy.__version__)" 2>&1 | tail -1
df -h /mnt/c ~ | tail -2
