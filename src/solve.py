import api

if __name__ == '__main__':
    print 'You are on level:', api.whoami()['level']

    cpu = api.cpu
    cpu.reset(debug=False)
    cpu._continue()
    while True:
        state = cpu.snapshot()
        step = state['state']
        output = state['new_output']
        if output:
            print output.decode('hex').strip()

        if step == '0':
            cpu._continue()
            continue

        if state['isdebug'] != 'false' or step == '2':
            cpu.reset(debug=False)

        if step == '4':
            cpu.send_input(raw_input('? '))
            cpu._continue()
