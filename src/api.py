import base64
import json
import requests
import urllib

from app import redis
import config


class ApiError(Exception):
    pass


class AuthError(ApiError):
    pass


def cookies():
    cookies = redis.get(config.COOKIE_KEY)
    if not cookies:
        raise AuthError('could not load cookies')
    return json.loads(cookies)


def csrf():
    csrf = redis.get(config.CSRF_KEY)
    if not csrf:
        raise AuthError('could not load csrf token')
    return csrf


def url(path):
    return config.PROXY_URL + '/' + path.lstrip('/')


def request(method, path, headers=None, **kwargs):
    headers = headers or {}
    headers.update({
        'X-CSRF-Token': csrf(),
    })
    r = requests.request(
        method, url(path), headers=headers, cookies=cookies(), **kwargs)
    try:
        return r.json()
    except Exception, e:
        print r.text


def get(path):
    return request('get', path)


def post(path, data=None, headers=None):
    headers = headers or {}
    headers.update({
        'content-type': 'application/json',
    })
    return request('post', path, data=json.dumps(data), headers=headers)


class CPU:
    regs = ['pc', 'sp', 'sr', 'sg']

    def get(self, path):
        return get(path)

    def post(self, path, data=None):
        headers = {
            'referer': url('/cpu/debugger'),
        }
        if not data:
            data = {'body': {}}
        return post(path, data=data, headers=headers)

    def set_reg(self, reg, value):
        self.post('/cpu/regs', {'reg': r, 'val': value})

    def set_mem(self, addr, value):
        self.post('/cpu/updatememory', {'addr': addr, 'val': value})

    # api endpoints
    def manual(self):
        return self.get('/get_manual')['manual']

    def load(self):
        self.post('/cpu/load')
        self.reset()

    def reset(self, debug=True):
        if debug:
            j = self.post('/cpu/reset/debug')
        else:
            j = self.post('/cpu/reset/nodebug')
        return j['data']['success']

    def send_input(self, data):
        self.post('/cpu/send_input', data={'body': data})

    def step_out(self):
        return self.post('/cpu/dbg/step_out')

    def step_over(self):
        return self.post('/cpu/dbg/step_over')

    def step(self, n=1):
        if n > 1:
            return self.post('/cpu/dbg/stepn/{}'.format(n))
        else:
            return self.post('/cpu/dbg/step')

    def breakpoints(self):
        return self.get('/cpu/dbg/events')

    def stepcount(self):
        return self.get('/cpu/dbg/stepcount')

    def _continue(self):
        return self.post('/cpu/dgb/continue')

    def _break(self, addr):
        return self.post('/cpu/dbg/event', data={'addr': addr, 'event': 0})

    def unbreak(self, addr):
        return self.post('/cpu/debug/event', data={'addr': addr, 'event': -1})

    def read(self, addr, length):
        data = self.get('/cpu/dbg/memory/{}?len={}'.format(addr, length))
        if data['error']:
            raise ApiError(data['error'])
        else:
            return base64.b64decode(data['raw'])

    def let(self, target, value):
        if target.startswith('r') or target in self.regs:
            if target in self.regs:
                i = target
            else:
                i = target.lstrip('r')
            self.set_reg(i, value)
        else:
            self.set_mem(i, value)

cpu = CPU()


def assemble(asm):
    return post('/assemble', data={'asm': asm})


def disasm(obj):
    return get('/cpu/dbg/disasm?obj=' + urllib.quote(obj))['data']['insns']


def whoami():
    return get('/whoami')
