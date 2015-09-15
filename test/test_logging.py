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

from __future__ import print_function

import pytest
import txaio
import mock

import logging

# from util import run_once

# XXX just use StringIO?
class TestHandler(object):
    def __init__(self, *args, **kw):
        self.messages = []
        self._data = ''

    def write(self, data):
        for line in data.split('\n'):
            line = line.strip()
            if line:
                self.messages.append(line)

    def flush(self):
        pass


@pytest.fixture(scope='session')
def log_started():
    """
    Sets up the logging, which we can only do once per run.
    """
    handler = TestHandler()
    txaio.start_logging(out=handler)
    return handler
"""
    if txaio.using_twisted:
# from twisted.logger import ILogObserver, formatEvent, Logger, LogPublisher
# from twisted.logger import LogLevel, globalLogBeginner, formatTime
        try:
            from twisted.logger import globalLogBeginner
            globalLogBeginner.beginLoggingTo([handler])
        except ImportError:
            from twisted.python import log
            log.startLogging(handler)
    else:
        logging.getLogger().addHandler(handler)
        logging.raiseExceptions = True
        logging.getLogger().setLevel(logging.DEBUG)
    return handler
"""


@pytest.fixture(scope='function')
def handler(log_started):
    """
    Resets the global TestHandler instance for each test.
    """
    log_started.messages = []
    return log_started


def test_critical(handler):
    logger = txaio.make_logger()

    # do something a little fancy, with attribute access etc.
    logger.critical(
        "{adjective} {nouns[2]}",
        adjective='hilarious',
        nouns=['skunk', 'elephant', 'wombat'],
    )

    assert len(handler.messages) == 1
    assert handler.messages[0].endswith("hilarious wombat")

def test_info(handler):
    logger = txaio.make_logger()

    # do something a little fancy, with attribute access etc.
    logger.info(
        "{adjective} {nouns[1]}",
        adjective='hilarious',
        nouns=['skunk', 'elephant', 'wombat'],
    )

    assert len(handler.messages) == 1
    assert handler.messages[0].endswith("hilarious elephant")

def test_debug_with_object(handler):
    logger = txaio.make_logger()

    class Shape(object):
        sides = 4
        name = "bamboozle"
        config = dict(foo='bar')

    logger.info(
        "{what.config[foo]} {what.sides} {what.name}",
        what=Shape(),
    )

    assert len(handler.messages) == 1
    assert handler.messages[0].endswith("bar 4 bamboozle")
