#!/usr/bin/env python

import re
import select
import socket
import threading
import time
import traceback

from app import redis
from arch.msp430 import CorruptionMSP
import config

command_re = re.compile(r'^(?P<ack>[+\-])|^\$(?P<data>[^#]*)#(?P<checksum>[a-f0-9]{2})')


def checksum(s):
    if s is None:
        return ''
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

def swapb(h):
    return ''.join(reversed([h[i:i + 2] for i in xrange(0, len(h), 2)]))


class GDBClient(object):
    def __init__(self, sock, cpu):
        self.sock = sock
        self.buf = ''
        self.out = []
        self.no_ack = False
        self.no_ack_test = False
        self.cpu = cpu

    def pump(self):
        raise NotImplementedError

    def recv(self):
        while True:
            if self.buf.startswith('\x03'):
                self.buf = self.buf[1:]
                yield '\x03'
                continue

            match = None
            if self.buf:
                match = command_re.match(self.buf)

            if match:
                add = len(match.group())
                self.buf = self.buf[add:]
                ack = match.group('ack')
                if ack:
                    if self.no_ack_test:
                        if ack == '+':
                            self.no_ack = True
                        self.no_ack_test = False
                else:
                    print '<- "{}"'.format(match.group())
                    data = match.group('data')

                    chk = match.group('checksum')
                    if checksum(data) == chk.lower():
                        self.ack()
                        yield unescape(data)
                    else:
                        print 'invalid chk'
                        self.nak()
            else:
                if self.buf and '$' in self.buf:
                    self.buf = ''.join(self.buf.split('$', 1)[1:])
                    self.nak()

                data = self.sock.recv(1024)
                if not data:
                    return

                self.buf += data

    def ack(self):
        if self.no_ack:
            return
        # print '-> "+"'
        self.sock.send('+')

    def nak(self):
        if self.no_ack:
            return
        # print '-> "-"'
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

class Client(GDBClient):
    def pump(self):
        for line in self.recv():
            if not line:
                self.nak()
                continue

            b = line[0]
            args = line[1:]
            if ':' in args:
                cmd, args = args.split(':', 1)
            else:
                cmd = args
                args = ''
            if b == '\x03':
                print 'eot' # ^C

            elif b == 'q': # query
                if cmd == 'Supported':
                    self.send('PacketSize=4000') # ;qXfer:features:read+') # ;qXfer:memory-map:read+')

                elif cmd == 'Attached':
                    self.send('1')

                elif cmd == 'Symbol':
                    self.send('OK')

                elif cmd == 'C':
                    self.send('OK')

                elif cmd == 'Xfer' and args.startswith('features:read:target.xml:'):
                    args = args.rsplit(':', 1)[1]
                    a, b = args.split(',', 1)
                    a, b = int(a, 16), int(b, 16)
                    self.send_tdesc(a, b)

                else:
                    self.send('')

            elif b == 'Q': # set query
                if cmd == 'StartNoAckMode':
                    self.no_ack_test = True
                else:
                    self.send('')

            elif b == 'g': # read registers
                self.send(''.join(swapb('%04x' % i) for i in self.cpu.read_regs()))

            elif b == 'G': # write registers
                regs = [int(swapb(cmd[i:i+4]), 16) for i in xrange(len(self.cpu.reg_names()))]
                self.cpu.write_regs(regs)

            elif b == 'M': # write memory
                addr, length = cmd.split(',', 1)
                addr, length = int(addr, 16), int(length, 16)
                self.cpu.write_mem(addr, args.decode('hex'))

            elif b == 'm': # read memory
                addr, length = cmd.split(',', 1)
                addr, length = int(addr, 16), int(length, 16)
                mem = self.cpu.read_mem(addr, length)
                self.send(mem.encode('hex'))

            elif b == 'c': # continue
                self.cpu._continue()
                self.wait()

            elif b == 's': # step
                if cmd:
                    n = int(cmd)
                else:
                    n = 1
                self.cpu.step(n)
                self.wait()

            elif b == '?': # last signal
                self.wait()

            elif b == 'H': # set the thread
                self.send('OK')

            else:
                print 'unknown command:', line
                self.send('')
                self.nak()

    def send_tdesc(self, addr, length):
        desc = self.cpu.tdesc()[addr:length]
        if desc:
            self.send('m' + desc)
        else:
            self.send('l')

    def wait(self):
        sig, pc = self.cpu.wait()
        self.send('T%02x%s:%s;thread:1;' % (sig, 'pc', swapb('%.4x' % pc)))


class MicroGDB(object):
    def __init__(self, cpu):
        self.cpu = cpu
        server = self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,
                          server.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) | 1)
        server.bind((config.GDB_HOST, config.GDB_PORT))
        server.listen(1)
        print 'Hosting GDB server on {}:{}'.format(*self.server.getsockname())

    def pump(self):
        while True:
            client, addr = self.server.accept()
            print 'GDB connection from {}:{}'.format(*addr)
            Client(client, cpu=self.cpu).run()
            print 'Lost connection to {}:{}'.format(*addr)


if __name__ == '__main__':
    import api
    gdb = MicroGDB(cpu=CorruptionMSP(api))
    try:
        gdb.pump()
    except KeyboardInterrupt:
        print
