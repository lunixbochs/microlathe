tdesc = '''<?xml version="1.0"?>
<!DOCTYPE target SYSTEM "gdb-target.dtd">
<target version="1.0">
<architecture>{arch}</architecture>
{features}
</target>
'''

features = '''
<feature name="info.bochs.msp430.m-profile">
{}
</feature>'''
register = '<reg name="{name}" bitsize="{bits}" type="{type}"/>'
