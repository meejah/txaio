from __future__ import absolute_import, print_function

import six
import sys
import traceback

from .interfaces import IFailedPromise

try:
    import asyncio
    from asyncio import iscoroutine
    from asyncio import Future
    from asyncio import async
    from asyncio import ALL_COMPLETED, FIRST_COMPLETED, FIRST_EXCEPTION

    from asyncio import coroutine

    if six.PY2:
        future_generator = coroutine

        def returnValue(x):
            print("OHAI", x)
            # inject the return value into the function-just-called
            raise Return(x)

    else:
        from .aio_py3asyncio import *


except ImportError:
    # Trollius >= 0.3 was renamed
    # noinspection PyUnresolvedReferences
    import trollius as asyncio
    from trollius import iscoroutine
    from trollius import Future
    from trollius import async
    from trollius import ALL_COMPLETED, FIRST_COMPLETED, FIRST_EXCEPTION

    from trollius import coroutine as future_generator

    from trollius import Return
    def returnValue(x):
        raise Return(x)


class FailedPromise(IFailedPromise):
    """
    This provides an object with any features from Twisted's Failure
    that we might need in Autobahn classes that use FutureMixin.

    We need to encapsulate information from exceptions so that
    errbacks still have access to the traceback (in case they want to
    print it out) outside of "except" blocks.
    """

    def __init__(self, type_, value, traceback):
        """
        These are the same parameters as returned from ``sys.exc_info()``

        :param type_: exception type
        :param value: the Exception instance
        :param traceback: a traceback object
        """
        self._type = type_
        self._value = value
        self._traceback = traceback

    @property
    def type(self):
        return self._type

    @property
    def value(self):
        return self._value

    @property
    def tb(self):
        return self._traceback

    def printTraceback(self, file=None):
        """
        Prints the complete traceback to stderr, or to the provided file
        """
        # print_exception handles None for file
        traceback.print_exception(self.type, self.value, self._traceback, file=file)

    def getErrorMessage(self):
        """
        Returns the str() of the underlying exception.
        """
        return str(self.value)

    def __str__(self):
        return self.getErrorMessage()

# API methods for txaio, exported via the top-level __init__.py

def create_future():
    return Future()

def create_future_success(result):
    f = Future()
    f.set_result(result)
    return f

def create_future_error(error=None):
    if error is None:
        error = create_failure()
    else:
        assert isinstance(error, IFailedPromise)
    f = Future()
    f.set_exception(error.value)
    return f

def as_future(fun, *args, **kwargs):
    try:
        res = fun(*args, **kwargs)
    except Exception:
        return create_future_error(create_failure())
    else:
        if isinstance(res, Future):
            return res
        elif iscoroutine(res):
            return asyncio.Task(res)
        else:
            return create_future_success(res)

def resolve_future(future, result):
    future.set_result(result)

def reject_future(future, error=None):
    if error is None:
        error = create_failure()  # will be error if we're not in an "except"
    else:
        assert isinstance(error, IFailedPromise)
    future.set_exception(error.value)

def create_failure():
    """
    This returns an object implementing IFailedPromise.

    It may ONLY be called within an "except" block (such that
    sys.exc_info() returns useful information).

    We create these objects so that errback()s can have a
    consistent API between asyncio and Twisted.
    """
    return FailedPromise(*sys.exc_info())

def add_future_callbacks(future, callback, errback):
    """
    callback or errback may be None, but at least one must be
    non-None.

    XXX in Twisted, if your callback returns something different,
    that's the value the next callback sees. In asyncio, this is not
    true (i.e. if you add 3 callbacks to a Future, they all see "the"
    value of the Future, not matter what they return).

    Currently, Autobahn doesn't depend on this (i.e. it always has one
    callback or is using closures so doesn't really care about the
    arg) but it's pretty inconsistent between the two platforms :/

    We can hack around it by setting _state on Future to avoid an
    error-check, but that seems fraught with the peril of using
    "private" stuff?
    """
    def done(f):
        print("DONE", f)
        try:
            res = f.result()
            print("real result=", res)
            if callback:
                x = callback(res)
                if x is not None:
                    f._result = x
        except Exception as e:
            if errback:
                print("ERRBACK", errback, e)
                errback(create_failure())
    return future.add_done_callback(done)

def gather_futures(futures,
                   consume_exceptions=True,
                   first_result=False,
                   first_exception=False):
    """
    This returns a Promise that waits for all the Promises in the list
    ``futures``, or the first result or error if you set
    ``first_result`` or ``first_exception``.

    :param futures: a list of Futures (or coroutines?)

    :param consume_exceptions: if True, any errors are eaten and NOT propagated

    :param first_result: if True, the Promise returns the first Promise that finishes

    :param first_exception: if True, the Promise errbacks with the first error

    Note that in ``asyncio``, both first_result and first_exception
    are not possible at the same time.
    """
    if first_result and first_exception:
        print("zinga")
        raise RuntimeError("Both first_result and first_exception not possible with asyncio")

    if first_result:
        when = FIRST_COMPLETED
    elif first_exception:
        when = FIRST_EXCEPTION
    else:
        when = ALL_COMPLETED

    print("WHEN", when)
    gen = asyncio.wait(futures, return_when=when)
    f = asyncio.async(gen)

    real_return = create_future()
    def unpack(future):
        print("UNPACK", future)
        (done, not_done) = future.result()
        print("done", done)
        print("NOT", not_done)
        results = []
        an_error = None
        for f in done:
            print("unpacking", f)
            try:
                value = f.result()
                ok = True
                # conceptually, we could short-circuit the loop here
                # if first_result is True, but asyncio gets grumpy if
                # you don't .result() on All The Things, so we
                # complete the whole loop and *then* return the first
                # result...

            except Exception as e:
                print("GOT EXCEPT", e)
                if an_error is None:
                    an_error = create_failure()
                if not consume_exceptions:
                    if first_exception:
                        print("REJECTING")
                        reject_future(real_return, an_error)
                        return
                value = e
                ok = False
            #results.append((ok, value))
            results.append(value)
        print("RES", results)
        if first_result:
            results = results[0]
        if an_error and not consume_exceptions:
            reject_future(real_return, an_error)
        else:
            resolve_future(real_return, results)
        return results

    f.add_done_callback(unpack)
    return real_return