#!/usr/bin/python3

'''PSHAW: Persistent Shell Archive Wrapper

Wrap a shell invocation inside a persistent session interface. The output log, command history, and current working directory are preserved. Reconnecting to the same session will restore them and allow you to continue working.

'''

import os, pty, re, shutil, subprocess, sys
from pathlib import Path

# Sanity checks. Log/history is pruned to this number of lines each
# time you disconnect from a session
logsize=1000000
historysize=1000000

usage_message = '''Usage:

    pshaw create <label>
    pshaw connect <label>
    pshaw list

create  -- Create a new session using <label> as the identifier and run a shell in that session.

connect -- Connect to an existing session with identifier <label>

list    -- List all sessions

'''

##########################################################################

def command_bash(lockpath='', shell='', initpath=''):
    return ['flock', '--nonblock', '--conflict-exit-code', '200', str(lockpath),
            str(shell), '--init-file', str(initpath), '-i']

##########################################################################

init_bash = '''

PSHAW_LABEL={label}
source {rcpath}

shopt -s histappend
HISTFILE={historypath}
cd `cat {workpath}`
PROMPT_COMMAND="history -a; pwd > {workpath}; $PROMPT_COMMAND"

echo === Connected to session {label} ===

'''

##########################################################################

def list():
    '''Print a list of sessions'''
    
    basepath = Path.home() / '.pshaw'
    for path in basepath.iterdir():
        if path.is_dir():
            print(path.name)

def create(label):
    '''Create a new session and then run a shell in it'''

    # Fail if session already exists
    basepath = Path.home() / '.pshaw' / label
    if basepath.exists():
        sys.stderr.write('Cannot create session: "{}" already exists.\n'.format(label))
        usage()

    # Make session directory at ~/.pshaw/label
    basepath.mkdir(parents=True, exist_ok=True)

    # Initialize output log and working directory files
    workpath = basepath / 'workdir'
    workpath.write_text(str(Path.cwd()), encoding='utf8')
    logpath = basepath / 'log'
    logpath.touch()

    run(label)

def connect(label):
    '''Connect a shell to an existing session'''

    # Fail if session does not exist
    basepath = Path.home() / '.pshaw' / label
    if not basepath.exists():
        sys.stderr.write('Cannot connect to session: "{}" not found\n'.format(label))
        usage()
        
    run(label)

def run(label):
    '''Run a shell in a session'''
    
    # Run a new instance of the current shell. Fail if shell is unsuported.
    shell = os.environ['SHELL']
    if shell != '/bin/bash':
        sys.stderr.write('Unknown Shell: {}\n'.format(shell))
        usage()

    # Setup paths to everything we need in the filesystem
    basepath = Path.home() / '.pshaw' / label
    initpath = basepath / 'init.bash'
    lockpath = basepath / 'lock'
    workpath = basepath / 'workdir'
    logpath = basepath / 'log'
    historypath = basepath / 'history'

    # Test for locked session (redundant, but provides cleaner error output)
    status = subprocess.run(['flock', '--nonblock', '--conflict-exit-code', '200',
                             str(lockpath), '/bin/true']).returncode
    if status == 200:
        sys.stderr.write('Cannot connect to session "{}": Session locked. If you are sure you are not already using this session, you can rm {} to unlock it.\n'.format(label, lockpath))
        exit(1)

    # Write initialization file. This sets up he shell to save the pwd
    # and history to the right place.
    data = {
        'label': label,
        'rcpath': str(Path.home() / '.bashrc'),
        'workpath': workpath,
        'historypath': historypath,
    }
    initpath.write_text(init_bash.format(**data), 'utf8')

    # Clear the terminal window including history
    sys.stdout.buffer.write(b'\033c')
    # Splat the entire history into the terminal so that we can scroll back
    with logpath.open('rb') as logfile:
        sys.stdout.buffer.write(logfile.read())
    sys.stdout.buffer.flush()
    
    # Run the command to lock the session and start the shell
    with logpath.open('ab') as logfile:
        def read(fd):
            data = os.read(fd, 1024)
            logfile.write(data)
            return data
        command = command_bash(shell=shell, initpath=initpath, lockpath=lockpath)
        status = pty.spawn(command, read)

    if status != 200:
        # On success, trim history and output log
        truncate(logpath, basepath / 'log.old', logsize)
        truncate(historypath, basepath / 'history.old', historysize)
        print('=== Disconnected from session "{}" ===\n'.format(label))
    else:
        # Failure means that we couldn't obtain the session lock
        sys.stderr.write('Cannot connect to session "{}": Session locked. If you are sure you are not already using this session, you can rm {} to unlock it.\n'.format(label, lockpath))
        exit(1)

def truncate(path, oldpath, size):
    '''Copy path file, then replace with a truncated (last size lines) version'''

    shutil.move(path, oldpath)
    with path.open('wb') as file:
        with subprocess.Popen(['tail', '-n', str(size), str(oldpath)],
                              stdout=subprocess.PIPE) as child:
            file.write(child.stdout.read())

##########################################################################

def usage():
    '''Print usage mesage and exit'''
    
    sys.stderr.write(usage_message)
    exit(1)

def parse_arguments():
    '''Find command and label. Return dictionary with results'''
    
    args = {}
    if len(sys.argv) <= 1 or len(sys.argv) > 3:
        usage()
    if sys.argv[1] == 'list':
        if len(sys.argv) != 2:
            usage()
        args['command'] = sys.argv[1]
    else:
        if (len(sys.argv) != 3 or
            (sys.argv[1] != 'create' and
             sys.argv[1] != 'connect')):
            usage()
        valid_label = re.compile('^[-0-9a-zA-Z]+$')
        if valid_label.match(sys.argv[2]) is None:
            sys.stderr.write('Invalid label {}: Must be [-a-zA-Z0-9]+\n'.format(sys.argv[2]))
        args['command'] = sys.argv[1]
        args['label'] = sys.argv[2]
    return args

def main():
    args = parse_arguments()
    if args['command'] == 'create':
        create(args['label'])
    elif args['command'] == 'connect':
        connect(args['label'])
    elif args['command'] == 'list':
        list()

main()
