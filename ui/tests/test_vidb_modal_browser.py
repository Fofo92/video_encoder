import sys
import io
from contextlib import redirect_stderr
import types
import unittest
from unittest.mock import Mock, patch

try:
    from PySide6 import QtCore, QtWidgets
except ModuleNotFoundError as error:
    if error.name != "PySide6":
        raise
    raise unittest.SkipTest("PySide6 is unavailable") from error

from video_encoder_ui import vidb_modal_browser as browser


class VidbModalBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_profile_identity_uses_only_the_server_not_request_tokens(self):
        self.assertEqual(browser.profile_key("https://vidb.test/episode?token=one"),
                         browser.profile_key("https://vidb.test/catalogue?token=two"))
        self.assertNotEqual(browser.profile_key("https://vidb.test"), browser.profile_key("https://other.test"))

    def test_refuses_non_https_or_credential_bearing_links(self):
        for url in ["file:///etc/passwd", "http://vidb.test", "https://name:secret@vidb.test"]:
            with self.assertRaises(ValueError):
                browser.profile_key(url)

    def test_missing_webengine_explains_installation_without_opening_a_tab(self):
        with patch.dict(sys.modules, {"PySide6.QtWebEngineCore": None, "PySide6.QtWebEngineWidgets": None}):
            widget = browser.build_vidb_browser(None, "https://vidb.test/catalogue")
        self.addCleanup(widget.deleteLater)
        self.assertIsInstance(widget, QtWidgets.QLabel)
        self.assertIn("python3-pyside6.qtwebenginewidgets", widget.text())

    def test_manual_review_uses_a_modal_dialog_instead_of_an_external_browser(self):
        view = QtWidgets.QLabel("vidb")
        self.addCleanup(view.deleteLater)
        with patch.object(browser, "build_vidb_browser", return_value=view) as build, \
             patch.object(browser.QtWidgets.QDialog, "exec", return_value=0) as execute:
            self.assertTrue(browser.open_vidb_modal(None, "https://vidb.test/episode"))
        build.assert_called_once()
        execute.assert_called_once()

    def test_browser_construction_error_keeps_an_explanatory_dialog_open(self):
        dialogs = []

        def fail(dialog, _url):
            dialogs.append(dialog)
            raise RuntimeError("internal request_token=private")

        with patch.object(browser, "build_vidb_browser", side_effect=fail), \
             patch.object(browser.QtWidgets.QDialog, "exec", return_value=0) as execute:
            self.assertFalse(browser.open_vidb_modal(None, "https://vidb.test/episode"))
        execute.assert_called_once()
        text = " ".join(label.text() for label in dialogs[0].findChildren(QtWidgets.QLabel))
        self.assertIn("RuntimeError", text)
        self.assertNotIn("private", text)
        dialogs[0].deleteLater()

    def test_page_load_failure_is_visible_without_closing_the_dialog(self):
        class View(QtWidgets.QLabel):
            loadFinished = QtCore.Signal(bool)

        view = View("page")
        self.addCleanup(view.deleteLater)

        def load_failure():
            view.loadFinished.emit(False)
            text = " ".join(label.text() for label in view.parentWidget().findChildren(QtWidgets.QLabel))
            self.assertIn("n’a pas pu être chargée", text)
            return 0

        with patch.object(browser, "build_vidb_browser", return_value=view), \
             patch.object(browser.QtWidgets.QDialog, "exec", side_effect=load_failure):
            self.assertTrue(browser.open_vidb_modal(None, "https://vidb.test/episode"))

    def test_opt_in_diagnostic_reports_lifecycle_without_the_requested_link(self):
        output = io.StringIO()
        view = QtWidgets.QLabel("vidb")
        self.addCleanup(view.deleteLater)
        with patch.dict(browser.os.environ, {"VIDEO_ENCODER_VIDB_DEBUG": "1"}), \
             redirect_stderr(output), \
             patch.object(browser, "build_vidb_browser", return_value=view), \
             patch.object(browser.QtWidgets.QDialog, "exec", return_value=0):
            browser.open_vidb_modal(None, "https://vidb.test/episode?request_token=private")
        self.assertIn("modal returned=0", output.getvalue())
        self.assertNotIn("private", output.getvalue())
        self.assertNotIn("request_token", output.getvalue())

    def test_successful_form_redirect_closes_the_manual_modal_without_a_second_click(self):
        class View(QtWidgets.QLabel):
            urlChanged = QtCore.Signal(QtCore.QUrl)

        view = View("vidb")
        self.addCleanup(view.deleteLater)
        observed = []

        def execute():
            view.urlChanged.emit(QtCore.QUrl("https://vidb.test/records/123?encoder_prepared=1"))
            self.app.processEvents()
            observed.append(view.parentWidget().result())
            return QtWidgets.QDialog.DialogCode.Accepted

        with patch.object(browser, "build_vidb_browser", return_value=view), \
             patch.object(browser.QtWidgets.QDialog, "exec", side_effect=execute):
            self.assertTrue(browser.open_vidb_modal(None, "https://vidb.test/encoder_projects/episode"))
        self.assertEqual([QtWidgets.QDialog.DialogCode.Accepted], observed)
