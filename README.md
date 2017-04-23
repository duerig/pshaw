# PSHAW: Persistent Shell Archive Wrapper

This script acts as a wrapper around shells to provide an
session-based archive of the history when using that shell. You can
use it as an enhanced 'script' command which records both the output
log and command history. Or you can use it to create resumable local
sessions which retain their scrollback, working directory, and command
history across exits and machine resets.

You create a new session by providing a label identifying it. You are
given a normal shell prompt using your current shell. The history file
of that shell prompt points to ~/.pshaw/<label>/history and is updated
with every command you enter. An output log is replicated to
~/.pshaw/<label>/log which is a raw dump of all the bytes that are put
into your screen. And whenever you change directories, the
~/.pshaw/<label>/pwd file is updated to reflect your new working
directory. Even after you exit, these files are saved to preserve your
history as an archive.

Later on, you can connect to the session again to resume work. Your
terminal window will be cleared and filled with the contents of the
output log to let you scroll back. The command history will be
restored. And your working directory will be changed to the one in
your pwd. Simple locking (with flock) is used to ensure that you don't
accidentally connect to the same session more than once at a time.

Unlike terminal multiplexers, none of this history is tied to any
running process. So if the machine reboots, you can return to your
history easily afterwards. But this also means that there is no way to
'detach' while processes are running or swap between sessions in the
same terminal window without exiting one and starting another.

The command history is tied to a particular shell. So if you run
another shell inside a session or SSH to a different machine, you will
see the output but the remote command history won't be stored. For
this reason, when doing remote work you would want to create a session
on the remote machine and use it from there rather than having a
session locally.

# Dependencies

* Python 3
* flock
* tee

# Supported Shells

* BASH

# Installation

`pshaw.py` is a standalone Python 3 script which can be run on most
Linux machines without modification.

1. Copy pshaw.py to a handy location. ex: cp pshaw.py ~/bin/pshaw
1. Make sure it is executable. ex: chmod u+x ~/bin/pshaw
1. Make sure that the location is in your path

# Usage

    pshaw create <label>
    pshaw connect <label>
    pshaw list

    create  -- Create a new session using <label> as the identifier and run a shell in that session.
    connect -- Connect to an existing session with identifier <label>
    list    -- List all sessions

