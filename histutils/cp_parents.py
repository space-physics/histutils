"""
This acts like bash cp --parents in Python
inspiration from
http://stackoverflow.com/questions/15329223/copy-a-file-into-a-directory-with-its-original-leading-directories-appended

example
source: /tmp/e/f
dest: /tmp/a/b/c/d/
result: /tmp/a/b/c/d/tmp/e/f

"""
from __future__ import unicode_literals
from pathlib2 import Path
from six import string_types
from shutil import copy2

def cp_parents(files,target_dir):
#%% make list if it's a string
    if isinstance(files,(string_types,Path)):
        files = [files]
#%% cleanup user
    files = (Path(f).expanduser() for f in files)   #relative path or absolute path is fine
    target_dir = Path(target_dir).expanduser()
#%% work
    for f in files:
        #leave str() on this line or it will break
        newpath = str(target_dir) +'/' +str(f.parent) #to make it work like cp --parents, copying absolute paths if specified
        Path(newpath).mkdir(parents=True, exist_ok=True)
        copy2(str(f), newpath)

#cp_parents('/tmp/a/b/c/d/boo','/tmp/e/f')
#cp_parents('x/hi','/tmp/e/f/g')  --> copies ./x/hi to /tmp/e/f/g/x/hi

if __name__ == '__main__':
    from sys import argv
    cp_parents(argv[1],argv[2])