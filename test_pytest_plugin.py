"""
This module tests our "pytest plugin" made available in
``napari.utils._testsupport``.  We leave this file in root so it is not
included in the sdist OR the wheel.
"""

import pytest


@pytest.mark.filterwarnings("ignore:`type` argument to addoption()::")
@pytest.mark.filterwarnings("ignore:The TerminalReporter.writer::")
def test_make_napari_viewer(testdir):
    """Make sure that our make_napari_viewer plugin works."""

    # create a temporary pytest test file
    testdir.makepyfile(
        """
        def test_make_viewer(make_napari_viewer):
            viewer = make_napari_viewer()
            assert viewer.layers == []
            assert viewer.__class__.__name__ == 'Viewer'
            assert not viewer.window._qt_window.isVisible()

    """
    )
    # run all tests with pytest
    result = testdir.runpytest()

    # check that all 1 test passed
    result.assert_outcomes(passed=1)
