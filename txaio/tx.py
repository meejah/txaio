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

import sys
import traceback

from twisted.python.failure import Failure
from twisted.internet.defer import maybeDeferred, Deferred, DeferredList
from twisted.internet.defer import succeed, fail
from twisted.internet.interfaces import IReactorTime

from zope.interface import provider

from txaio.interfaces import IFailedFuture, ILogger
from txaio import _Config

import six

using_twisted = True
using_asyncio = False

config = _Config()
_stderr, _stdout = sys.stderr, sys.stdout
_observer = None  # we keep this here to support Twisted legacy logging; see below

IFailedFuture.register(Failure)

_NEW_LOGGER = False
try:
    # if we just demand this, what version of Twisted do we need?
    # (15.x? 13.2 doesn't work, anyway)
    # globalLogPublisher
    from twisted.logger import Logger, formatEvent, ILogObserver
    from twisted.logger import globalLogBeginner, formatTime, LogLevel
    ILogger.register(Logger)
    _NEW_LOGGER = True

except ImportError:
    from twisted.python import log
    from functools import partial
    from zope.interface import Interface
    from datetime import datetime
    import time

    class ILogObserver(Interface):
        pass

    def formatTime(t):
        dt = datetime.fromtimestamp(t)
        return unicode(dt.strftime("%Y-%m-%dT%H:%M:%S%z"))

    def formatEvent(event):
        msg = event['log_format']
        return msg.format(**event)

    class Logger(ILogger):
        def __init__(self):
            levels = ['critical', 'error', 'warn', 'info', 'debug', 'trace']
            for level in levels:
                setattr(self, level, partial(self._do_log, level))

        def _do_log(self, level, message, **kwargs):
            global _observer
            assert _observer is not None, "Call txaio.start_logging before logging"
            kwargs['log_time'] = time.time()
            kwargs['log_level'] = level
            kwargs['log_format'] = message
            _observer(kwargs)

        def failure(self, message, **kwargs):
            global _observer
            assert _observer is not None, "Call txaio.start_logging before logging"
            kwargs['log_failure'] = Failure()
            kwargs['log_level'] = 'critical'
            kwargs['log_format'] = message
            kwargs['log_time'] = time.time()
            _observer(kwargs)


def make_logger():
    return Logger()


@provider(ILogObserver)
class _LogObserver(object):
    """
    Internal helper.

    An observer which formats events to a given file.
    """
    def __init__(self, out, levels):
        self._file = out
        self._levels = levels

    def __call__(self, event):
        # XXX FIXME as per discussion, we should make the actual
        # log-methods no-ops to deal with levels!
        if event["log_level"] not in self._levels:
            return

        # if False:
        #     log_sys = event.get("log_namespace", "")
        #     if len(log_sys) > 30:
        #         log_sys = log_sys[:3] + '..' + log_sys[-25:]
        #     msg ="[{:<30}] {}\n".format(log_sys, formatEvent(event))
        #     self._file.write(msg)

        if 'log_failure' in event:
            self._file.write(
                '{} {}\n{}'.format(
                    formatTime(event['log_time']),
                    event['log_format'],
                    traceback.format_exc(),
                )
            )
        else:
            msg = '{} {}\n'.format(formatTime(event["log_time"]), formatEvent(event))
            self._file.write(msg)



def start_logging(out=None):
    """
    Start logging to the file-like object in ``out``. By default, this
    is stdout.
    """
    if out is None:
        out = _stdout
    if _NEW_LOGGER:
        levels = [LogLevel.critical, LogLevel.error, LogLevel.warn, LogLevel.info, LogLevel.debug]
    else:
        levels = ['critical', 'error', 'warn', 'info', 'debug', 'trace']
    global _observer
    _observer = _LogObserver(out, levels)
    if _NEW_LOGGER:
        globalLogBeginner.beginLoggingTo([_observer])
    else:
        from twisted.python import log
        log.startLogging(out)


def failure_message(fail):
    """
    :param fail: must be an IFailedFuture
    returns a unicode error-message
    """
    return '{}: {}'.format(
        fail.value.__class__.__name__,
        fail.getErrorMessage(),
    )


def failure_traceback(fail):
    """
    :param fail: must be an IFailedFuture
    returns a traceback instance
    """
    return fail.tb


def failure_format_traceback(fail):
    """
    :param fail: must be an IFailedFuture
    returns a string
    """
    f = six.StringIO()
    fail.printTraceback(file=f)
    return f.getvalue()


_unspecified = object()


def create_future(result=_unspecified, error=_unspecified):
    if result is not _unspecified and error is not _unspecified:
        raise ValueError("Cannot have both result and error.")

    f = Deferred()
    if result is not _unspecified:
        resolve(f, result)
    elif error is not _unspecified:
        reject(f, error)
    return f


# maybe delete, just use create_future()
def create_future_success(result):
    return succeed(result)


# maybe delete, just use create_future()
def create_future_error(error=None):
    return fail(create_failure(error))


# maybe rename to call()?
def as_future(fun, *args, **kwargs):
    return maybeDeferred(fun, *args, **kwargs)


def call_later(delay, fun, *args, **kwargs):
    return IReactorTime(_get_loop()).callLater(delay, fun, *args, **kwargs)


def resolve(future, result=None):
    future.callback(result)


def reject(future, error=None):
    if error is None:
        error = create_failure()
    elif isinstance(error, Exception):
        error = Failure(error)
    else:
        if not isinstance(error, Failure):
            raise RuntimeError("reject requires a Failure or Exception")
    future.errback(error)


def create_failure(exception=None):
    """
    Create a Failure instance.

    if ``exception`` is None (the default), we MUST be inside an
    "except" block. This encapsulates the exception into an object
    that implements IFailedFuture
    """
    if exception:
        return Failure(exception)
    return Failure()


def add_callbacks(future, callback, errback):
    """
    callback or errback may be None, but at least one must be
    non-None.
    """
    assert future is not None
    if callback is None:
        assert errback is not None
        future.addErrback(errback)
    else:
        # Twisted allows errback to be None here
        future.addCallbacks(callback, errback)
    return future


def gather(futures, consume_exceptions=True):
    def completed(res):
        rtn = []
        for (ok, value) in res:
            rtn.append(value)
            if not ok and not consume_exceptions:
                value.raiseException()
        return rtn

    # XXX if consume_exceptions is False in asyncio.gather(), it will
    # abort on the first raised exception -- should we set
    # fireOnOneErrback=True (if consume_exceptions=False?) -- but then
    # we'll have to wrap the errback() to extract the "real" failure
    # from the FirstError that gets thrown if you set that ...

    dl = DeferredList(list(futures), consumeErrors=consume_exceptions)
    # we unpack the (ok, value) tuples into just a list of values, so
    # that the callback() gets the same value in asyncio and Twisted.
    add_callbacks(dl, completed, None)
    return dl


# methods internal to this implementation


def _get_loop():
    if config.loop is None:
        from twisted.internet import reactor
        config.loop = reactor
    return config.loop
