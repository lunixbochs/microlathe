from common import tdesc, features, register


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


class CorruptionMSP(object):
    def __init__(self, api):
        # super(self.__class__, self).__init__()
        self.api = api
        self.cpu = api.cpu

    def read_regs(self):
        snapshot = self.cpu.snapshot()
        return snapshot['regs']

    def write_regs(self, regs):
        for name, value in zip(self.reg_names(), regs):
            self.cpu.let(name, value)

    def read_mem(self, addr, length):
        return ''.join(
            self.cpu.read(i, min(length, 1024))
            for i in xrange(addr, addr + length, 1024)
        )[:length]

    def write_mem(self, addr, data):
        print 'write_mem stub'

    def _continue(self):
        self.cpu._continue()

    def step(self, n=1):
        self.cpu.step(n)
