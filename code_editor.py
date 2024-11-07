import os
from pathlib import Path
import sys
import re
from PySide6.QtCore import (QFile, Qt, QTextStream, QRect)
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QKeySequence, QBrush,
                           QSyntaxHighlighter, QTextCharFormat, QTextFormat, QPainter, QPen)
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow,
                               QPlainTextEdit, QFrame, QWidget, QTextEdit, QHBoxLayout)


class Highlighter(QSyntaxHighlighter):
    def __init__(self, is_code=False, is_diff=False, parent=None):
        QSyntaxHighlighter.__init__(self, parent)

        self._mappings = {}
        self._diff_mappings = {}

        self.line_cnt = 1

        self.is_code = is_code
        self.is_diff = is_diff

        self.added_lines = []
        self.removed_lines = []

    def add_mapping(self, pattern, format):
        self._mappings[pattern] = format

    def add_diff_mapping(self, line, format, status):
        self._diff_mappings[line] = format

        if status:
            self.added_lines.append(line)
        else:
            self.removed_lines.append(line)

    def clear_diff(self):
        self._diff_mappings = {}
        self.added_lines = []
        self.removed_lines = []

    def highlightBlock(self, text):

        if self.is_code:
            for pattern, format in self._mappings.items():
                for match in re.finditer(pattern, text):
                    start, end = match.span()
                    self.setFormat(start, end - start, format)

        if self.is_diff and self._diff_mappings:
            for line, format in self._diff_mappings.items():
                if line == self.line_cnt:
                    self.setFormat(0, len(text), format)

        self.line_cnt += 1


class LNTextEdit(QFrame):

    def __init__(self, *args):
        QFrame.__init__(self, *args)

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)

        self.edit = self.PlainTextEdit()
        self.number_bar = self.NumberBar(self.edit)

        hbox = QHBoxLayout(self)
        hbox.setSpacing(0)
        # hbox.setMargin(0)
        hbox.addWidget(self.number_bar)
        hbox.addWidget(self.edit)

        self.edit.blockCountChanged.connect(self.number_bar.adjustWidth)
        self.edit.updateRequest.connect(self.number_bar.updateContents)

    class NumberBar(QWidget):

        def __init__(self, edit):
            QWidget.__init__(self, edit)

            self.edit = edit
            self.adjustWidth(10)

        def paintEvent(self, event):
            self.edit.numberbarPaint(self, event)
            QWidget.paintEvent(self, event)

        def adjustWidth(self, count):
            # width = self.fontMetrics().width(count)   # unicode(count)
            # if self.width() != width:
            #     self.setFixedWidth(width)
            if self.edit.double_line_number:
                if len(self.edit._added_lines) > 0 or len(self.edit._removed_lines) > 0:
                    self.setFixedWidth((len(str(count)) * 10) * 2 + 40)
                else:
                    self.setFixedWidth((len(str(count)) * 10) * 2 + 20)
            else:
                self.setFixedWidth((len(str(count)) * 10) + 10)

        def adjustWidth_diff(self, count):

            self.setFixedWidth(len(str(count))*8 + 10)

        def updateContents(self, rect, scroll):
            if scroll:
                self.scroll(0, scroll)
            else:
                # It would be nice to do
                # self.update(0, rect.y(), self.width(), rect.height())
                # But we can't because it will not remove the bold on the
                # current line if word wrap is enabled and a new block is
                # selected.
                self.update()

    class PlainTextEdit(QPlainTextEdit):

        def __init__(self, *args):
            QPlainTextEdit.__init__(self, *args)

            #self.setFrameStyle(QFrame.NoFrame)

            self.setFrameStyle(QFrame.NoFrame)
            self.highlight()
            #self.setLineWrapMode(QPlainTextEdit.NoWrap)

            self.cursorPositionChanged.connect(self.highlight)

            self.double_line_number = False
            self._added_lines = []
            self._removed_lines = []

        def set_diff_line(self, added=[], removed=[]):
            self.double_line_number = True
            self._added_lines = added
            self._removed_lines = removed

        def highlight(self):
            hi_selection = QTextEdit.ExtraSelection()

            hi_selection.format.setBackground(self.palette().alternateBase())
            # hi_selection.format.setProperty(QTextFormat.FullWidthSelection, QVariant(True))
            hi_selection.cursor = self.textCursor()
            hi_selection.cursor.clearSelection()

            self.setExtraSelections([hi_selection])

        def numberbarPaint(self, number_bar, event):
            font_metrics = self.fontMetrics()
            current_line = self.document().findBlock(self.textCursor().position()).blockNumber() + 1

            block = self.firstVisibleBlock()
            line_count = block.blockNumber()
            painter = QPainter(number_bar)
            painter.fillRect(event.rect(), self.palette().base())

            added_line_cnt = 0
            removed_line_cnt = 0

            # Iterate over all visible text blocks in the document.
            while block.isValid():
                line_count += 1
                block_top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()

                # Check if the position of the block is out side of the visible
                # area.
                if not block.isVisible(): # or block_top & gt ;= event.rect().bottom():
                    break

                # We want the line number for the selected line to be bold.
                font = painter.font()

                if line_count == current_line:
                    font.setBold(True)
                else:
                    font.setBold(False)

                painter.setFont(font)

                rect_colot = QColor("#FFD141")
                if self.double_line_number:
                    if line_count in self._added_lines:
                        print('>>> line_count: ', line_count, ' , self._added_lines: ', self._added_lines)
                        rect_colot = QColor("#dae8bc")

                    if line_count in self._removed_lines:
                        print('>>> line_count: ', line_count, ' , self._removed_lines: ', self._removed_lines)
                        rect_colot = QColor("#f29b9b")

                brush = QBrush()
                brush.setColor(rect_colot)
                brush.setStyle(Qt.SolidPattern)
                painter.setBrush(brush)

                pen = QPen()
                # pen.setWidth(3)
                pen.setColor(rect_colot)
                painter.setPen(pen)

                # Draw the line number right justified at the position of the line.
                # print(">>>>>>>>> block_top: ", block_top)
                # print(">>>>>>>>> number_bar.width(): ", number_bar.width())
                # print(">>>>>>>>> font_metrics.height(): ", font_metrics.height())
                if self.double_line_number:
                    bar_width = int((number_bar.width()) / 2 - 4)
                    marker_space = 18

                    add_space = -1
                    if len(self._added_lines) > 0 or len(self._removed_lines) > 0:
                        add_space = -1

                    # print('>>>>> bar_width: ', bar_width)
                    # print('>>>>> add_space: ', add_space)

                    paint_rect = QRect(0, block_top, bar_width-add_space, int(font_metrics.height()))
                    paint_rect_d = QRect(bar_width-add_space, block_top, int(number_bar.width()) - marker_space, int(font_metrics.height()))
                    paint_rect_m = QRect(bar_width-add_space+marker_space, block_top, marker_space, int(font_metrics.height()))
                else:
                    paint_rect = QRect(0, block_top, int(number_bar.width()), int(font_metrics.height()))

                painter.fillRect(paint_rect, brush)
                if self.double_line_number:
                    # print('>>>>> display double line for rect')
                    painter.fillRect(paint_rect_d, brush)
                    if len(self._added_lines) > 0 or len(self._removed_lines) > 0:
                        painter.fillRect(paint_rect_m, brush)

                pen.setColor(QColor("#05080f"))
                painter.setPen(pen)

                if self.double_line_number:
                    # print('>>>>> display double line for text')
                    line1_text = '  ' + str(line_count - removed_line_cnt)
                    line2_text = '  ' + str(line_count - added_line_cnt)
                    marker = ' '

                    if line_count in self._added_lines:
                        print('>>> line_count: ', line_count, ' , self._added_lines: ', self._added_lines)
                        # line2_text = '  ' + str(line_count) + '  +'
                        line1_text = '  ' + str(line_count - removed_line_cnt)
                        line2_text = '  '
                        marker = '+'
                        added_line_cnt += 1
                    if line_count in self._removed_lines:
                        print('>>> line_count: ', line_count, ' , self._removed_lines: ', self._removed_lines)
                        # line2_text = '  ' + str(line_count) + '  -'
                        line1_text = '  '
                        line2_text = '  ' + str(line_count - added_line_cnt)
                        marker = '-'
                        removed_line_cnt += 1

                    painter.drawText(paint_rect, Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, line1_text)
                    painter.drawText(paint_rect_d, Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, line2_text)
                    painter.drawText(paint_rect_m, Qt.AlignmentFlag.AlignRight | Qt.TextFlag.TextWordWrap, marker)
                else:
                    line1_text = '  ' + str(line_count)
                    painter.drawText(paint_rect, Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, line1_text)

                block = block.next()

            painter.end()

    def getText(self):
        return self.edit.toPlainText()  # unicode(self.edit.toPlainText())

    def setText(self, text):
        self.edit.setPlainText(text)

    def isModified(self):
        return self.edit.document().isModified()

    def setModified(self, modified):
        self.edit.document().setModified(modified)

    def setLineWrapMode(self, mode):
        self.edit.setLineWrapMode(mode)
