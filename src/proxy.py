from flask import (
    Response,
    request,
)
import requests

from config import PROXY_HOST, PROXY_URL

response_blacklist = (
    'accept-ranges',
    'connection',
    'content-encoding',
    'content-length',
    'expires',
    'set-cookie',
)

request_blacklist = ('content-length', 'host') 


def swap_request_host(s):
    if s.startswith('http') and PROXY_URL.startswith('https'):
        s = s.replace('http://', 'https://', 1)
    return s.replace(request.host, PROXY_HOST)


def swap_response_host(s):
    if s.startswith('https'):
        s = s.replace('https://', 'http://', 1)
    return s.replace(PROXY_HOST, request.host)


def clean_headers(headers, request=True):
    remap = {}
    if request:
        remap['referer'] = swap_request_host
        blacklist = request_blacklist
    else:
        remap['location'] = swap_response_host
        blacklist = response_blacklist

    out = {}
    for key, value in headers.items():
        k = key.lower()
        if k in blacklist:
            continue

        if k in remap:
            value = remap[k](value)

        out[key] = value
    return out


def proxy(path=''):
    url = PROXY_URL + '/' + path
    host = request.host
    data = request.environ['body_copy']

    headers = clean_headers(request.headers, request=True)

    cookies = request.cookies
    kwargs = {
        'allow_redirects': False,
        'cookies': cookies,
        'headers': headers,
    }
    if data:
        kwargs['data'] = data

    response = requests.request(request.method, url, **kwargs)
    content_type = response.headers.get('content-type', 'text/plain')
    r = Response(response.content)
    for k, v in clean_headers(response.headers, request=False).items():
        r.headers[k] = v

    for c in response.cookies:
        r.set_cookie(c.name, c.value)

    r.status_code = response.status_code
    return r
