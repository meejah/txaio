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

from __future__ import absolute_import

import abc
import six

@six.add_metaclass(abc.ABCMeta)
class ILogger(object):
    """
    This defines the methods you can call on the object returned from
    :meth:`txaio.make_logger` -- although the actual object may have
    additional methods, you should *only* call the methods listed
    here.

    All the log methods have the same signature, they just differ in
    what "log level" they represent to the handlers/emitters. The
    ``message`` argument is a format string, which can include
    embedded ``{`` and ``}`` delimited references to things from the
    ``kwargs``. For example:

        class MyThing(object):
            logger = txaio.make_logger()

            def something_interesting(self, things=dict(one=1, two=2)):
                try:
                    logger.debug("Calling with {things[one]}", things=things)
                    result = self._method_call(things['one'])
                    logger.info("Got '{result}'.", result=result)
                except Exception:
                    # for .failure, the kwargs will magically contain
                    # ``log_failure`` in this case, which is an
                    # IFailedFuture. A stack-trace will be printed.
                    logger.failure("Sadness: {log_failure.value}")

    Recommendation: use ``.failure()`` for unexpected errors, and
    ``.critical()`` for errors a user might reasonably see.
    """

# stdlib notes:
# levels:
#   CRITICAL 50
#   ERROR 40
#   WARNING 30
#   INFO 20
#   DEBUG 10
#   NOTSET 0


# NOTES
# things in Twisted's event:
# - log_level
# - log_failure (sometimes?)
# - log_message
# - log_source (sometimes?)
#
# .warn not warning!

    def critical(self, message, **kwargs):
        "log a critical-level message"

    def error(self, message, **kwargs):
        "log a error-level message"

    def warning(self, message, **kwargs):
        "log a error-level message"

    def info(self, message, **kwargs):
        "log an info-level message"

    def debug(self, message, **kwargs):
        "log an debug-level message"

    def trace(self, message, **kwargs):
        "log a trace-level message"

    def failure(self, message, **kwargs):
        """
        Log an exception, at level critical. Call with ``except:`` block.

        This also logs a stack-trace (in addition to the message
        provided).  As such, it is intended for unexpected errors.

        A key ``log_failure`` (an instance of IFailedFuture) is
        available for formatting the message
        (e.g. "{log_failure.value}").  This IFailedFuture wraps the
        current exception, so you **MAY ONLY CALL** .failure within an
        ``except:`` block.
        """


@six.add_metaclass(abc.ABCMeta)
class IFailedFuture(object):
    """
    This defines the interface for a common object encapsulating a
    failure from either an asyncio task/coroutine or a Twisted
    Deferred.

    An instance implementing this interface is given to any
    ``errback`` callables you provde via :meth:`txaio.add_callbacks`

    In your errback you can extract information from an IFailedFuture
    with :meth:`txaio.failure_message` and
    :meth:`txaio.failure_traceback` or use ``.value`` to get the
    Exception instance.

    Depending on other details or methods will probably cause
    incompatibilities between asyncio and Twisted.
    """

    @abc.abstractproperty
    def value(self):
        """
        An actual Exception instance. Same as the second item returned from
        ``sys.exc_info()``
        """
