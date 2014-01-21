import re
import select
import socket
import threading
import time
import traceback

from app import redis
import config

command_re = re.compile(r'^(?P<ack>[+\-])|^\$(?P<data>[^#]*)#(?P<checksum>[a-f0-9]{2})')


def checksum(s):
    return '%0.2x' % (sum([ord(c) for c in s]) % 256)


def escape(s):
    out = []
    for c in s:
        if c in '#$}':
            c = (ord(c) ^ 0x20)
        out.append(c)
    return ''.join(out)


def unescape(s):
    out = []
    i = 0
    while i < len(s) - 1:
        c = s[i]
        if c == '}':
            c = (ord(s[i + 1]) ^ 0x20)
            i += 1
        out.append(c)
        i += 1

    return ''.join(out)


class Client(object):
    def __init__(self, sock):
        self.sock = sock
        self.buf = ''

    def pump(self):
        for line in self.recv():
            if not line:
                self.send('')
                continue

            b = line[0]
            args = line[1:]
            if b == 'q': # query
                self.ack()
                if 'Supported' in args:
                    self.send('PacketSize=400')
                else:
                    self.send('')
            elif b == 'g': # read registers
                self.send('XXXXXXXX')
            elif b == 'G': # write registers
                self.ack()
            elif b == 'm': # read memory
                self.ack()
            elif b == 'M': # write memory
                self.ack()
            elif b == 'c': # continue
                self.ack()
            elif b == 's': # step
                self.ack()
            elif b == '?': # last signal
                self.ack()
                self.send('S05')
            elif b == 'H':
                self.ack()
                self.send('OK')
            else:
                print 'unknown command:', line
                self.send('')
                self.nak()

    def recv(self):
        while True:
            ready, _, _ = select.select([self.sock], [], [], 0.1)
            if not ready:
                continue

            data = self.sock.recv(1024)
            if not data:
                return

            self.buf += data
            match = command_re.match(self.buf)
            if match:
                print '<- "{}"'.format(match.group())
                add = len(match.group())
                self.buf = self.buf[add:]
                if match.group('ack'):
                    pass
                else:
                    data = match.group('data')
                    chk = match.group('checksum')
                    if checksum(data) == chk.lower():
                        yield unescape(data)
                    else:
                        print 'invalid chk'
                        self.nak()
            else:
                print 'um', self.buf
                self.buf = ''.join(self.buf.split('$', 1)[1:])
                self.nak()

    def ack(self):
        print '-> "+"'
        self.sock.send('+')

    def nak(self):
        print '-> "-"'
        self.sock.send('-')

    def send(self, data=''):
        data = escape(data)
        data = '$' + data + '#' + checksum(data)
        print '-> "{}"'.format(data)
        self.sock.send(data)

    def run(self):
        try:
            self.pump()
        except socket.error, e:
            print e
        except Exception:
            traceback.print_exc()
        finally:
            self.close()

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


class MicroGDB(object):
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((config.GDB_HOST, config.GDB_PORT))
        self.server.listen(1)
        print 'Hosting GDB server on {}:{}'.format(*self.server.getsockname())

    def pump(self):
        while True:
            client, addr = self.server.accept()
            print 'GDB connection from {}:{}'.format(*addr)
            Client(client).run()
            print 'Lost connection to {}:{}'.format(*addr)


def spawn():
    gdb = MicroGDB()
    thread = threading.Thread(target=gdb.pump)
    thread.daemon = True
    thread.start()
