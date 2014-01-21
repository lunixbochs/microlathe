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

    out.append(s[-1])
    return ''.join(out)


class Client(object):
    def __init__(self, sock):
        self.sock = sock
        self.buf = ''
        self.need_ack = False
        self.out = []
        self.no_ack = False
        self.no_ack_queue = False

    def pump(self):
        for line in self.recv():
            if not line:
                self.nak()
                continue

            self.ack()
            b = line[0]
            args = line[1:]
            if ':' in args:
                cmd, args = args.split(':', 1)
            else:
                cmd = args
                args = ''
            if b == 'q': # query
                if cmd == 'Supported':
                    self.queue('PacketSize=3fff') # ;QStartNoAckMode+')
                elif cmd == 'Attached':
                    self.queue('1')
                elif cmd == 'Symbol':
                    self.queue('OK')
                elif cmd == 'C':
                    self.queue('OK')
                else:
                    self.queue('')
            elif b == 'Q': # set query
                if cmd == 'StartNoAckMode':
                    self.ack()
                    self.queue('OK')
                    self.no_ack_queue = True
                else:
                    self.queue('')
            elif b == 'g': # read registers
                self.queue('1234')
            elif b == 'G': # write registers
                pass
            elif b == 'm': # read memory
                pass
            elif b == 'M': # write memory
                pass
            elif b == 'c': # continue
                pass
            elif b == 's': # step
                pass
            elif b == '?': # last signal
                self.queue('S05')
            elif b == 'H': # set the thread
                self.queue('OK')
            else:
                print 'unknown command:', line
                self.queue('')
                self.nak()

    def recv(self):
        while True:
            ready, _, _ = select.select([self.sock], [], [], 0.1)
            if not ready:
                continue

            match = command_re.match(self.buf)
            if match:
                print '<- "{}"'.format(match.group())
                add = len(match.group())
                self.buf = self.buf[add:]
                ack = match.group('ack')
                if ack:
                    self.got_ack(ack)
                else:
                    data = match.group('data')
                    chk = match.group('checksum')
                    if checksum(data) == chk.lower():
                        yield unescape(data)
                    else:
                        print 'invalid chk'
                        self.nak()
            else:
                if self.buf and '$' in self.buf:
                    print 'might be truncating', self.buf.split('$', 1)[0]
                    self.buf = ''.join(self.buf.split('$', 1)[1:])
                    self.nak()

                data = self.sock.recv(1024)
                if not data:
                    return

                self.buf += data

    def ack(self):
        if self.no_ack:
            return
        print '-> "+"'
        self.sock.send('+')

    def nak(self):
        if self.no_ack:
            return
        print '-> "-"'
        self.sock.send('-')

    def send(self, data=''):
        data = escape(data)
        data = '$' + data + '#' + checksum(data)
        print '-> "{}"'.format(data)
        self.sock.send(data)

    def queue(self, data=''):
        if self.no_ack:
            self.send(data)
        elif not self.need_ack:
            self.send(data)
            self.out.append(data)
            self.need_ack = True
        else:
            self.out.append(data)

    def got_ack(self, ack):
        print 'got_ack', ack, self.out
        if self.no_ack:
            return

        if self.no_ack_queue:
            self.no_ack_queue = False
            if ack == '+':
                self.no_ack = True

        if ack == '+' and self.out:
            self.out.pop(0)
        if self.out:
            self.send(self.out[0])
        else:
            self.need_ack = False

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
