'''
We try to support Windows so we can't use bash scripts.
'''

import os
import sys

# 1. Check python 3.11 is installed
print('Checking python 3.11 is installed...')
try:
    assert sys.version_info >= (3, 11)
except AssertionError:
    print('Python 3.11 is required. Please install it.')
    sys.exit(1)
    
# 2. Install packages
'''
'''

def pip_install_from_path(path):
    if os.system(f'pip install -e {path}') != 0:
        print(f'Failed to install {path}')
        sys.exit(1)

print('Installing packages...')
pip_install_from_path('topicsync')
pip_install_from_path('objectsync')
pip_install_from_path('backend')
pip_install_from_path('extensions/grapycal_builtin')

print('Installation complete. Run `python main.py` to start the server.')