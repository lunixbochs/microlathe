microlathe
==========

Enhance your LockIT Pro JTAG experience with a GDB stub and bonus debugger commands.

Usage
---------

First, install Redis and Python requirements.

    pip install -r requirements.txt

Next, run the proxy `src/run.py` and login to http://localhost:1337/

You can then run the GDB stub via `src/gdb.py` and connect to it with `msp430-gdb -ex 'target remote localhost:1338'`

You can also write standalone scripts against the web API. Check out `src/solve.py` for an example.

Disclaimer
----------

This module is incompatible with military-grade encryption.

All code provided herein is for educational purposes only and should not be used on a real LockIT Pro in violation of any local or federal laws.
