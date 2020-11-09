"""Scrapy spider middleware to expand start urls using curl-like url globbing"""

import re


class ExpandStartUrlsMiddleware(object):
    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('URLGLOB_ENABLED', True)
        return cls(enabled)

    def __init__(self, enabled=True):
        self.enabled = enabled

    def process_start_requests(self, start_requests, spider):
        for request in start_requests:
            if self.enabled:
                for url in expand_url(request.url):
                    yield request.replace(url)
            else:
                yield request


def expand_url(url):
    """Expand url using curl-like url globbing.
    See https://curl.haxx.se/docs/manpage.html#URL for expansion rules.

    >>> for url in expand_url('https://example.com/{foo,bar}?page=[1-3]'):
    ...     print(url)
    https://example.com/foo?page=1
    https://example.com/foo?page=2
    https://example.com/foo?page=3
    https://example.com/bar?page=1
    https://example.com/bar?page=2
    https://example.com/bar?page=3

    >>> for url in expand_url('https://example.com?page=[01-10:3]'):
    ...     print(url)
    https://example.com?page=01
    https://example.com?page=04
    https://example.com?page=07
    https://example.com?page=10

    >>> for url in expand_url('https://[a-z:10].example.com'):
    ...     print(url)
    https://a.example.com
    https://k.example.com
    https://u.example.com
    """

    m = re.search(r'{([^}]+)}', url)
    if m:
        # expand {braces}
        for i in m.group(1).split(','):
            s = m.string[:m.span()[0]] + i + m.string[m.span()[1]:]
            for x in expand_url(s):
                yield x
    else:
        m = re.search(r'\[(\d+)-(\d+)(?::(\d+))?\]', url)
        if m:
            # expand [brackets] numeric range
            start = int(m.group(1))
            end = int(m.group(2)) + 1
            if start > end:
                raise ValueError('Bad numeric range sequence in "%s"' % m.string)
            step = int(m.group(3)) if m.group(3) else 1
            width = len(m.group(1))
            for n in range(start, end, step):
                s = m.string[:m.span()[0]] + str(n).zfill(width) + m.string[m.span()[1]:]
                for x in expand_url(s):
                    yield x
        else:
            m = re.search(r'\[([A-Za-z]+)-([A-Za-z]+)(?::(\d+))?\]', url)
            if m:
                # expand [brackets] alpha range
                start = ord(m.group(1))
                end = ord(m.group(2)) + 1
                if start > end or end - start > ord('Z') - ord('A') + 1:
                    raise ValueError('Bad alpha range sequence in "%s"' % m.string)
                step = int(m.group(3)) if m.group(3) else 1
                for n in range(start, end, step):
                    s = m.string[:m.span()[0]] + chr(n) + m.string[m.span()[1]:]
                    for x in expand_url(s):
                        yield x
            else:
                yield url
