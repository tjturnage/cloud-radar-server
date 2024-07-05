from time import sleep
from pathlib import Path

source_dir = '/home/tjt/public_html/public/radar/KGRR'
p = Path(source_dir)
dirFile = p.joinpath('/home/tjt/public_html/public/radar/KGRR','dir.list')
try:
    dirFile.unlink()
except:
    pass

files = list(p.glob('*gz'))
dir_list_lines = []

output = ''
for f in files:
    sleep(10)
    line = f'{f.stat().st_size} {f.parts[-1]}\n'
    output = output + line
    print(line)
    
    with open(dirFile,mode='w') as fout:
        fout.write(output)

