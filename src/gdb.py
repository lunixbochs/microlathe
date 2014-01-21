import threading
import time

from app import redis
import config


class MicroGDB(object):
    def pump(self):
        while True:
            time.sleep(1)


def spawn():
    gdb = MicroGDB()
    thread = threading.Thread(target=gdb.pump)
    thread.daemon = True
    thread.start()
