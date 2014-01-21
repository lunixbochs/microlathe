PROXY_HOST = 'microcorruption.com'
PROXY_URL = 'https://{}'.format(PROXY_HOST)

REDIS_PREFIX = 'microcorruption_'
COOKIE_KEY = REDIS_PREFIX + 'cookies'
CSRF_KEY = REDIS_PREFIX + 'csrf'
