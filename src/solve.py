import sys

import api

if __name__ == '__main__':
    print 'You are on level:', api.whoami()['level']

    cpu = api.cpu
    cpu.reset(debug=False)
    cpu._continue()
    inputs = []
    while True:
        state = cpu.snapshot()
        step = state['state']
        output = state['new_output']
        if output:
            print output.decode('hex').strip()

        if state['advanced'] == 'win':
            print 'Input:', inputs
            print 'Win! ({} cycles, {} bytes)'.format(state['advanced_steps'], sum([len(i) for i in inputs]))
            sys.exit(0)

        if step == '0':
            cpu._continue()
            continue

        if state['isdebug'] != 'false' or step == '2':
            cpu.reset(debug=False)
            inputs = []

        if step == '4':
            text = raw_input('? ')
            inputs.append(text)
            cpu.send_input(text)
            cpu._continue()
