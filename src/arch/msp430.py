from common import tdesc, features, register
import time


class MSP430(object):
    def __init__(self):
        self.regs = [0] * len(self.reg_names())

    @classmethod
    def reg_names(cls):
        add = tuple('r{}'.format(i) for i in xrange(4,16))
        return ('pc', 'sp', 'sr', 'cg') + add

    @classmethod
    def tdesc(cls):
        regs = '\n'.join([register.format(**{
            'name': reg, 'bits': 16, 'type': 'int16',
        }) for reg in cls.reg_names()])

        feature = features.format(regs)
        return tdesc.format(
            arch='msp430',
            features=feature,
        )

    def read_regs(self):
        return [0 for n in self.regs]

    def write_regs(self, regs):
        self.regs = regs

    def reg(self, name):
        return self.read_regs()[self.reg_names().index(name)]


class MemBuffer(object):
    def __init__(self, read, size=256):
        self.read_raw = read
        self.clear()
        self.size = size

    def clear(self):
        self.pages = {}

    def get_pages(self, start, end):
        out = []
        for base in xrange(start, end, self.size):
            if base in self.pages:
                page = self.pages[base]
            else:
                page = self.pages[base] = self.read_raw(base, self.size)
            out.append(page)
        return ''.join(out)

    def read(self, addr, length):
        start = addr & ~(self.size - 1)
        end = addr + length
        clip = addr - start
        pages = self.get_pages(start, end)
        return pages[clip:clip+length]


class CorruptionMSP(object):
    def __init__(self, api):
        # super(self.__class__, self).__init__()
        self.api = api
        self.cpu = api.cpu
        self.cache = MemBuffer(self.read_mem_raw)

    def read_regs(self):
        snapshot = self.cpu.snapshot()
        return snapshot['regs']

    def write_regs(self, regs):
        for name, value in zip(self.reg_names(), regs):
            self.cpu.let(name, value)

    def read_mem_raw(self, addr, length):
        return ''.join(
            self.cpu.read(i, min(length, 1024))
            for i in xrange(addr, addr + length, 1024)
        )[:length]

    def read_mem(self, addr, length):
        return self.cache.read(addr, length)

    def write_mem(self, addr, data):
        print 'write_mem stub'

    def _continue(self):
        self.cache.clear()
        self.cpu._continue()

    def step(self, n=1):
        self.cache.clear()
        self.cpu.step(n)

    def wait(self, timeout=30):
        start = time.time()
        while time.time() - start < timeout:
            state = self.cpu.snapshot()
            step = int(state['state'])
            pc = state['regs'][0]
            if step == 4:
                print 'we need input'
            elif step == 2:
                return 3, pc
            elif step == 1:
                print 'running'
            elif step == 0:
                return 0, pc

            time.sleep(0.5)

        return 0, 0
