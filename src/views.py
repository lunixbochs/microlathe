from bs4 import BeautifulSoup
from datetime import timedelta
from flask import (
    request,
    Response,
)
import json
from werkzeug.routing import Rule

import api
from app import app, redis
import config
import proxy

app.url_map.add(Rule('/', endpoint='proxy'))
app.url_map.add(Rule('/<path:path>', endpoint='proxy'))


@app.endpoint('proxy')
def router(path=''):
    if request.cookies:
        redis.setex(
            config.COOKIE_KEY,
            json.dumps(request.cookies),
            timedelta(minutes=120),
        )
    response = proxy.proxy(path)
    if 'text/html' in response.content_type and 'csrf-token' in response.data:
        soup = BeautifulSoup(response.data)
        meta = soup.find('meta', attrs={'name':'csrf-token'})
        if meta:
            redis.setex(
                config.CSRF_KEY,
                meta['content'],
                timedelta(minutes=120),
            )
    return response


@app.route('/proxy/mem.bin')
def bonus_dump():
    mem = ''.join(api.cpu.read(i, i + 1024) for i in xrange(0, 0xffff, 1024))
    return Response(mem, content_type='application/octet_stream')
