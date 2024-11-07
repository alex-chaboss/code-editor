from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
                               QMainWindow, QApplication, QFrame, QWidgetItem)
from PySide6.QtCore import QTimer, QRunnable, Slot, Signal, QObject, QThreadPool, QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import (QFile, Qt, QTextStream)
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QKeySequence, QBrush,
                           QSyntaxHighlighter, QTextCharFormat)
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow,
                               QPlainTextEdit, QFrame)

import re
import signal
import sys
import time
import traceback

from code_editor import Highlighter, LNTextEdit


class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    '''
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int)


''' Class to parallel work '''
class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @Slot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


""" MainWindow using to start and use PySide6 """
class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.counter = 0
        self.base_text = ''
        self.code_text = ''
        self.original_text = ''
        self.worker_on_work = False

        self.setWindowTitle("Widgets App")

        # self.view = QQuickView()
        # self.container = QWidget.createWindowContainer(self.view, self)
        # self.container.setMinimumSize(250, 250)
        # self.container.setMaximumSize(250, 250)
        # self.view.setSource(QUrl("gui/qml/Main.qml"))

        # self.view.show()
        # self.layout.addWidget(self.container, 1, Qt.AlignBottom)
        self.label = QLabel("Start")
        button = QPushButton("Make Original")
        button.setFixedWidth(200)
        button.setStyleSheet("QPushButton { background-color: #86a950; color: black;}")
        button.pressed.connect(self.make_original)
        self._highlighter = Highlighter(True, False)
        self._highlighter_baseDiff = Highlighter(True, True)

        ln_editor = LNTextEdit()

        self.setup_file_menu()

        self.init_editors()
        # self.setup_base_diff()

        # editor = CodeEditor()
        # editor.file.open(code_edit.__file__)

        layoutV = QVBoxLayout()
        layoutH = QHBoxLayout()

        widgetsH = [
            # self.container,
            # self.label,
            # ln_editor,

            self._editor,
            self._editor_base
        ]

        for widget in widgetsH:
            layoutH.addWidget(widget)

        editors_widget = QWidget()
        editors_widget.setLayout(layoutH)

        widgetsV = [
            # self.container,
            # self.label,
            # ln_editor,
            button,
            editors_widget
        ]

        for widget in widgetsV:
            layoutV.addWidget(widget)

        central_widget = QWidget()
        central_widget.setLayout(layoutV)

        self.setCentralWidget(central_widget)
        # self.show()

        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

    def make_original(self):
        text = self._editor.edit.document().toPlainText()
        self._highlighter_baseDiff.clear_diff()
        self._editor_base.edit.set_diff_line(self._highlighter_baseDiff.added_lines,
                                             self._highlighter_baseDiff.removed_lines)
        self._editor_base.edit.clear()
        self.show_diff()
        # time.sleep(1)
        self._editor_base.edit.setPlainText(text)
        # time.sleep(1)
        self.code_text = text
        self.base_text = text
        self.original_text = text

    def progress_fn(self, n):
        # print("%d%% done" % n)
        pass

    def execute_this_fn(self, progress_callback):
        for n in range(0, 5):
            time.sleep(1)
            progress_callback.emit(n*100/4)

        return "Done."

    def print_output(self, s):
        # print('>>>>>> len new base: ', len(s))
        self._editor_base.edit.clear()
        self._editor_base.edit.set_diff_line(self._highlighter_baseDiff.added_lines, self._highlighter_baseDiff.removed_lines)
        self._editor_base.edit.setPlainText(s)
        self.show_diff()

    def thread_complete(self):
        print("THREAD COMPLETE!")
        self.worker_on_work = False

    # def test(self):
    #     # Pass the function to execute
    #     worker = Worker(self.execute_this_fn)  # Any other args, kwargs are passed to the run function
    #     worker.signals.result.connect(self.print_output)
    #     worker.signals.finished.connect(self.thread_complete)
    #     worker.signals.progress.connect(self.progress_fn)
    #     self.worker_on_work = True
    #     # Execute
    #     self.threadpool.start(worker)

    def base_text_change(self):
        print('>>>>> base_text_change start !')

    def code_text_change(self):
        print('>>>>> code_text_change start !')
        worker = Worker(self.merge_and_diff)
        worker.signals.result.connect(self.print_output)
        worker.signals.finished.connect(self.thread_complete)
        worker.signals.progress.connect(self.progress_fn)

        # Execute
        if not self.worker_on_work:
            self.threadpool.start(worker)
            self.worker_on_work = True

    def merge_and_diff(self, progress_callback):
        print('>>>>> merge_and_diff start !')
        # QApplication.processEvents()
        code_block_cnt = self._editor.edit.document().blockCount()
        base_block_cnt = self._editor_base.edit.document().blockCount()
        print('>>>>>>> code_block_cnt: ', code_block_cnt)
        print('>>>>>>> base_block_cnt: ', base_block_cnt)

        new_base_text = ''

        base_cnt = 1
        code_cnt = 1
        additional_cnt = 0

        if base_block_cnt <= 1:
            return self.base_text
        else:
            self._editor_base.edit.setPlainText(self.original_text)
            self._highlighter_baseDiff.clear_diff()

        block = self._editor.edit.document().firstBlock()
        base_block = self._editor_base.edit.document().firstBlock()

        while block.isValid():
            code_line = block.text()
            base_line = base_block.text()
            # print('>>>>>>> code_cnt: ', code_cnt)
            # print('>>>>>>> base_cnt: ', base_cnt)
            # print('>>>>>>> additional_cnt: ', additional_cnt)
            # print('>>>>>>> code_line: ', code_line)
            # print('>>>>>>> base_line: ', base_line)

            if code_line == base_line:
                new_base_text += (base_line + '\n') if (base_block.next().isValid() or block.next().isValid()) else base_line
                base_cnt += 1
                code_cnt += 1

                block = block.next()
                if base_block.next().isValid():
                    base_block = base_block.next()
            else:
                base_text = self._editor_base.edit.document().toPlainText()
                code_text = self._editor.edit.document().toPlainText()

                base_text = base_text.split('\n')[base_cnt:]
                code_text = code_text.split('\n')[code_cnt:]

                # print('>>>>> block.isValid(): ', block.isValid(), ' , base_line in code_text: ', base_line in code_text, ' , code_line != base_line: ', code_line != base_line)

                if (base_line in code_text) and block.isValid():
                    # print('>>>>>>> base_line in code: ', code_text[0])
                    new_base_text += (code_line + '\n') if (base_block.next().isValid() or block.next().isValid()) else base_line
                    self.highlighter_diffPattern(True, base_cnt + additional_cnt, '1')
                    code_cnt += 1
                    additional_cnt += 1
                    while code_line != base_line and block.isValid():
                        block = block.next()
                        code_line = block.text()
                        if code_line != base_line:
                            new_base_text += (code_line + '\n') if (base_block.next().isValid() or block.next().isValid()) else base_line
                            self.highlighter_diffPattern(True, base_cnt + additional_cnt, '2')
                            code_cnt += 1
                            additional_cnt += 1
                        if code_cnt > (code_block_cnt + base_block_cnt + 10) or base_cnt > (
                                code_block_cnt + base_block_cnt + 10):
                            break

                # print('>>>>> base_block.isValid(): ', base_block.isValid(), ' , code_line in base_text: ', code_line in base_text, ' , code_line != base_line: ', code_line != base_line)
                # print('>>>>>>> next code_line: ', code_line)
                # print('>>>>>>> next base_line: ', base_line)

                if (code_line in base_text) and code_line != base_line and base_block.isValid():
                    new_base_text += (base_line + '\n') if (base_block.next().isValid() or block.next().isValid()) else base_line
                    self.highlighter_diffPattern(False, base_cnt + additional_cnt, '3')
                    base_cnt += 1
                    while code_line != base_line and base_block.isValid():
                        base_block = base_block.next()
                        base_line = base_block.text()
                        if code_line != base_line:
                            new_base_text += (base_line + '\n') if (base_block.next().isValid() or block.next().isValid()) else base_line
                            self.highlighter_diffPattern(False, base_cnt + additional_cnt, '4')
                            base_cnt += 1
                        if code_cnt > (code_block_cnt + base_block_cnt + 10) or base_cnt > (
                                code_block_cnt + base_block_cnt + 10):
                            break

                if (code_line not in base_text) and code_line != base_line and (base_block.isValid() or block.isValid()) and (base_line not in code_text):
                    new_base_text += (code_line + '\n') if (base_block.next().isValid() or block.next().isValid()) else base_line
                    self.highlighter_diffPattern(True, base_cnt + additional_cnt, '5')
                    code_cnt += 1
                    new_base_text += (base_line + '\n') if (base_block.next().isValid() or block.next().isValid()) else base_line
                    base_cnt += 1
                    self.highlighter_diffPattern(False, base_cnt + additional_cnt, '6')
                    additional_cnt += 1
                    base_block = base_block.next()
                    block = block.next()
            progress_callback.emit(base_cnt * 100 / base_block_cnt)
            if code_cnt > (code_block_cnt + base_block_cnt + 10) or base_cnt > (code_block_cnt + base_block_cnt + 10):
                break

        QApplication.processEvents()
        return new_base_text

    def setup_file_menu(self):
        file_menu = self.menuBar().addMenu(self.tr("&File"))

        new_file_act = file_menu.addAction(self.tr("&New..."))
        new_file_act.setShortcut(QKeySequence(QKeySequence.New))
        new_file_act.triggered.connect(self.new_file)

        open_file_act = file_menu.addAction(self.tr("&Open..."))
        open_file_act.setShortcut(QKeySequence(QKeySequence.Open))
        open_file_act.triggered.connect(self.open_file)

        quit_act = file_menu.addAction(self.tr("E&xit"))
        quit_act.setShortcut(QKeySequence(QKeySequence.Quit))
        quit_act.triggered.connect(self.close)

    def new_file(self):
        self.code_text = ''
        self.base_text = ''
        self.original_text = ''
        self._editor_base.edit.clear()
        self._editor.edit.clear()

    def open_file(self, path=""):
        file_name = path

        if not file_name:
            file_name, _ = QFileDialog.getOpenFileName(self, self.tr("Open File"), "",
                                                       "Python Files (*.py)")

        if file_name:
            in_file = QFile(file_name)
            if in_file.open(QFile.ReadOnly | QFile.Text):
                stream = QTextStream(in_file)
                text = stream.readAll()

                self._highlighter_baseDiff.clear_diff()

                self.code_text = text
                self.base_text = text
                self.original_text = text

                # time.sleep(1)
                self._editor_base.edit.clear()
                self._editor_base.edit.setPlainText(text)
                # time.sleep(1)
                self._editor.edit.clear()
                self._editor.edit.setPlainText(text)
                # time.sleep(1)

    def highlighter_codePattern(self):
        """ Try to add patterns for code style """
        class_format = QTextCharFormat()
        class_format.setFontWeight(QFont.Bold)
        class_format.setForeground(Qt.blue)
        pattern = r'^\s*class\s+\w+.*$'
        self._highlighter.add_mapping(pattern, class_format)
        self._highlighter_baseDiff.add_mapping(pattern, class_format)

        import_format = QTextCharFormat()
        import_format.setFontWeight(QFont.Bold)
        import_format.setForeground(Qt.red)
        pattern = r'((from\s)|(import\s)|(\stry)|(True)|(False)|(\sif)|(\selif)|(\selse)|(\sexcept)|(\sfinally))'
        self._highlighter.add_mapping(pattern, import_format)
        self._highlighter_baseDiff.add_mapping(pattern, import_format)

        function_format = QTextCharFormat()
        function_format.setFontItalic(True)
        function_format.setForeground(Qt.blue)
        pattern = r'^\s*def\s+\w+\s*\(.*\)\s*:\s*$'
        self._highlighter.add_mapping(pattern, function_format)
        self._highlighter_baseDiff.add_mapping(pattern, function_format)

        comment_format = QTextCharFormat()
        # comment_format.setBackground(QColor("#999999"))
        comment_format.setForeground(QColor("#999999"))
        comment_format.setFontItalic(True)
        pattern = r"(\s#.*$)"
        self._highlighter.add_mapping(pattern, comment_format)
        self._highlighter_baseDiff.add_mapping(pattern, comment_format)

        comment_format = QTextCharFormat()
        # comment_format.setBackground(QColor("#999999"))
        comment_format.setForeground(QColor("#999999"))
        comment_format.setFontItalic(True)
        # pattern = r"(\'{3}((.|\n)*?)\'{3})"
        pattern = r"(((\'{3})|(\"{3}))((.|\n|\s|\0|\t|\r)*?)((\'{3})|(\"{3})))"
        self._highlighter.add_mapping(pattern, comment_format)
        self._highlighter_baseDiff.add_mapping(pattern, comment_format)

    def highlighter_diffPattern(self, is_new, line, marker=''):
        # print('>>>>> highlighter_diffPattern --> is_new: ', is_new, ' , line: ', line, ' , marker: ', marker)
        if is_new:
            diff_format_add = QTextCharFormat()
            brush = QBrush(QColor("#dae8bc"), Qt.SolidPattern)
            # diff_format_add.setForeground(QColor("#999999"))
            # diff_format_add.setFontItalic(True)
            # diff_format_add.setBackground(QColor("#dae8bc"))
            diff_format_add.setBackground(brush)
            self._highlighter_baseDiff.add_diff_mapping(line, diff_format_add, is_new)
        else:
            diff_format_remove = QTextCharFormat()
            brush = QBrush(QColor("#f29b9b"), Qt.SolidPattern)
            # keyword.setForeground(brush)
            # diff_format_remove.setForeground(QColor("#999999"))
            # diff_format_remove.setFontItalic(True)
            diff_format_remove.setBackground(brush)
            # diff_format_remove.setBackground(QColor("#f29b9b"))
            self._highlighter_baseDiff.add_diff_mapping(line, diff_format_remove, is_new)

    def show_diff(self):
        self._highlighter_baseDiff.line_cnt = 1
        font2 = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self._editor_base.edit.setFont(font2)
        self._highlighter_baseDiff.setDocument(self._editor_base.edit.document())

    def init_editors(self):
        self.highlighter_codePattern()
        # self.highlighter_diffPattern(True, 17)
        # self.highlighter_diffPattern(False, 20)

        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)

        # self._editor = QPlainTextEdit()
        self._editor = LNTextEdit()

        self._editor.edit.setFont(font)
        self._editor.edit.textChanged.connect(self.code_text_change)
        self._highlighter.setDocument(self._editor.edit.document())

        font2 = QFontDatabase.systemFont(QFontDatabase.FixedFont)

        # self._editor_base = QPlainTextEdit()
        self._editor_base = LNTextEdit()

        self._editor_base.edit.setFont(font2)
        # self._editor_base.edit.textChanged.connect(self.base_text_change)
        self._editor_base.edit.setReadOnly(True)
        self._editor_base.edit.set_diff_line(self._highlighter_baseDiff.added_lines, self._highlighter_baseDiff.removed_lines)
        self._highlighter_baseDiff.setDocument(self._editor_base.edit.document())


QML_IMPORT_NAME = "editor"
QML_IMPORT_MAJOR_VERSION = 1

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setOrganizationName('Chaboss')
    app.setOrganizationDomain('ChabossWorld')

    window = MainWindow()
    window.resize(1200, 800)
    window.show()
    app.exec()

