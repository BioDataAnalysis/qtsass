# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2015 Yann Lanthony
# Copyright (c) 2017-2018 Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (See LICENSE.txt for details)
# -----------------------------------------------------------------------------
"""Test qtsass cli."""

from __future__ import absolute_import

# Standard library imports
import time
import os
import shutil
from os.path import dirname, exists

# Third party imports
import pytest

#Local imports
from qtsass import compile_filename
from qtsass.watchers import PollingWatcher, QtWatcher

from . import EXAMPLES_DIR, example, touch, await_condition


class CallCounter(object):

    def __init__(self):
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1


@pytest.mark.parametrize(
    'Watcher', (PollingWatcher, QtWatcher),
)
def test_watchers(Watcher, tmpdir):
    """Stress test Watcher implementations"""

    # Skip when QtWatcher is None - when Qt is not installed.
    if not Watcher:
        return

    watch_dir = tmpdir.join('src').strpath
    os.makedirs(watch_dir)
    shutil.copy2(example('dummy.scss'), watch_dir)
    input = tmpdir.join('src/dummy.scss').strpath
    output = tmpdir.join('build/dummy.css').strpath
    output_exists = lambda: exists(output)

    c = CallCounter()
    w = Watcher(
        watch_dir=watch_dir,
        compiler=compile_filename,
        args=(input, output),
    )
    w.connect(c)

    # Output should not yet exist
    assert not exists(output)

    w.start()

    touch(input)
    time.sleep(0.5)
    if not await_condition(output_exists):
        assert False, 'Output file not created...'

    # Removing the watch_dir should not kill the Watcher
    # simply stop dispatching callbacks
    shutil.rmtree(watch_dir)
    time.sleep(0.5)
    assert c.count == 1

    # Watcher should recover once the input file is there again
    os.makedirs(watch_dir)
    shutil.copy2(example('dummy.scss'), watch_dir)
    time.sleep(0.5)
    assert c.count == 2

    # Stop watcher
    w.stop()
    w.join()

    for _ in range(5):
        touch(input)

    # Count should not change
    assert c.count == 2


def test_qtwatcher(tmpdir):
    """Test QtWatcher implementation"""

    # Skip when QtWatcher is None - When Qt is not installed
    if not QtWatcher:
        return

    # Constructing a QApplication will cause the QtWatcher constructed
    # below to use a Signal to dispatch callbacks.
    from qtsass.watchers.qt import QApplication

    qt_app = QApplication.instance()
    if not qt_app:
        qt_app = QApplication([])

    watch_dir = tmpdir.join('src').strpath
    os.makedirs(watch_dir)
    shutil.copy2(example('dummy.scss'), watch_dir)
    input = tmpdir.join('src/dummy.scss').strpath
    output = tmpdir.join('build/dummy.css').strpath
    output_exists = lambda: exists(output)

    c = CallCounter()
    w = QtWatcher(
        watch_dir=watch_dir,
        compiler=compile_filename,
        args=(input, output),
    )
    # We connect a counter directly to the Watcher's Qt Signal in order to
    # verify that the Watcher is actually using a Qt Signal.
    w.qtdispatcher.signal.connect(c)
    w.start()

    touch(input)
    time.sleep(0.5)
    if not await_condition(output_exists, qt_app=qt_app):
        assert False, 'Output file not created...'
    assert c.count == 1

    # Stop watcher
    w.stop()
    w.join()
