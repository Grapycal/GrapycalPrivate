import os
import pathlib
import shutil
import argparse

ignores = [
    '.git',
    '.gitignore',
    '.vscode',
    '__pycache__',
    'node_modules',
]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('dist', type=str, help='The name of the distribution.')
    parser.add_argument('--template', type=str, default='source', help='The template folder to be the base of the distribution. The folder can have install scripts and other necessary files.')
    args = parser.parse_args()
    
    root = pathlib.Path(__file__).parent
    template = root / 'templates' / args.template
    dst_root = root / 'dist' / args.dist

    if dst_root.exists():
        response = input(f'{dst_root} already exists. Overwrite? [y/N] ')
        if response.lower() != 'y':
            print('Aborted.')
            exit()
        else:
            shutil.rmtree(dst_root)

    shutil.copytree(template, dst_root)

    # build frontend
    os.system('python scripts/build_frontend.py')

    def copy(src, dst=None):
        if dst is None:
            dst = src
        print(f'Copying {src} to {dst}')
        shutil.copytree(src, dst_root / dst, ignore=shutil.ignore_patterns(*ignores))
    
    copy('backend')
    copy('submodules/topicsync/', 'topicsync')
    copy('submodules/objectsync/', 'objectsync')
    copy('frontend/dist', 'frontend')
    copy('extensions/grapycal_builtin')
    copy('entry')

    print(f'Packaged to {dst_root} with {__file__.split(os.sep)[-1]}')
    size = sum(f.stat().st_size for f in dst_root.rglob('*') if f.is_file())
    print(f'Size: {size / 1024:.2f} KB' if size < 1024 * 1024 else f'Size: {size / 1024 / 1024:.2f} MB')