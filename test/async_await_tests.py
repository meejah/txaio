###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Tavendo GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

# note that these tests are only imported from *inside* the "actual"
# test cases in "test_async_await.py" because we can't even load this
# file on non-Python-3.5+ platforms (but we want to just skip these
# tests in that case, not fail entirely).

import pytest
import txaio

from util import run_once


def _test_as_future_async(framework):
    print("doing the thing", framework, txaio.using_twisted)
    # this test only makes sense for Python3.5+ and Twisted
    txaio.use_twisted()
    
    calls = []
    results = []
    errors = []
    futures = []
    
    async def method0(*args, **kw):
        calls.append(('method0', args, kw))
        d = txaio.create_future()
        futures.append(d)
        return await method1(d)

    async def method1(d):
        print("about to await", d)
        x = await d
        calls.append(('method1', x))
        return x

    f = txaio.as_future(method0, 1, 2, 3, key='word')

    def cb(x):
        results.append(x)

    def errback(f):
        errors.append(f)

    txaio.add_callbacks(f, cb, errback)

    run_once()
    assert len(futures) == 1
    txaio.resolve(futures[0], 'foo')
    run_once()

    assert len(errors) == 0, errors
    assert len(calls) == 2, "expected 2 calls to succeed"
    assert len(results) == 1, "expected a single result"
    assert results[0] == 'foo'
