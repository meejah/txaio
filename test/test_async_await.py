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

import pytest
import txaio

# we need to keep the "actual" tests in a separate file because we
# must perform the above import test before even trying to read the
# file (beacuse "async def foo" is a syntax error before Python 3.5)

def test_as_future_async(framework):
    print("here we go")
    try:
        from asyncio import iscoroutinefunction
        from twisted.internet.defer import ensureDeferred
        if txaio.using_twisted:
            from async_await_tests import _test_as_future_async
            return _test_as_future_async(framework)
        else:
            print("un-Twisted")
    except ImportError as e:
        print("Skipping", e)
        pytest.skip("Only for Python3.5 + Twisted: {}".format(e))

