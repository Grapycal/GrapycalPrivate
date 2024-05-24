import os
import shutil
from pathlib import Path
import sys

def execute_instruction(line):
	args = line.split(' ')
	match args[0]:
		case "u":  # update
			source_folder, name = args[1], args[2]
			if os.path.isfile(name):
				os.remove(name)
			shutil.move(Path(source_folder) / name, '.')
		case "rmtree":  # remove dir
			folder = args[1]
			shutil.rmtree(folder)
		case "r":  # run python script
			script = args[1]
			exec(open(script).read())


with open('update', 'r') as f:
	for line in f.readlines():
		execute_instruction(line.strip())
os.remove('update')

# sys.argv[0] is updater.py, sys.argv[1:] is the original argv when executing main.py
os.execv(sys.executable, ['python'] + sys.argv[1:])