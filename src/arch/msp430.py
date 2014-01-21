from common import tdesc, features, register

class MSP430(object):
    @classmethod
    def registers(cls):
        add = tuple('r{}'.format(i) for i in xrange(4,16))
        return ('pc', 'sp', 'sr', 'cg') + add

    @classmethod
    def tdesc(cls):
        regs = '\n'.join([register.format(**{
            'name': reg, 'bits': 16, 'type': 'int16',
        }) for reg in cls.registers()])

        feature = features.format(regs)
        return tdesc.format(
            arch='msp430',
            features=feature,
        )
