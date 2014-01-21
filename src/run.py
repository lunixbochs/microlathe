#!/usr/bin/env python

import os
import sys

import app

if __name__ == '__main__':
    port = 1337
    if len(sys.argv) == 2:
        port = int(sys.argv[1])

    app.app.root_path = os.path.dirname(app.__file__)
    app.app.run(port=port, threaded=True, use_reloader=True, debug=True)
