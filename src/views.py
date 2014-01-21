from bs4 import BeautifulSoup
from datetime import timedelta
from flask import (
    abort,
    g,
    request,
    Response,
)
import json
import requests
from werkzeug.routing import Rule

from app import app, redis
import config
import proxy


app.url_map.add(Rule('/', endpoint='proxy'))
app.url_map.add(Rule('/<path:path>', endpoint='proxy'))

response_blacklist = (
    'accept-ranges',
    'connection',
    'content-encoding',
    'content-length',
    'expires',
    'set-cookie',
)
request_blacklist = ('content-length', 'content-type', 'host', 'cookie')

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
