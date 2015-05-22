"""
helpbrowser.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'

from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from cecog.util.pattern import QSingleton

__all__ = ['HelpBrowser']


class HelpBrowser(QtWidgets.QDialog):
    """Help browser for the CecogAnalyzer. This class is a singleton."""

    __metaclass__ = QSingleton

    QRC_TOKEN = 'qrc:/'

    def __init__(self, *args, **kw):
        super(HelpBrowser, self).__init__(*args, **kw)

        self.setWindowTitle("CecogAnalyzer Help Browser")
        self.setMinimumSize(QtCore.QSize(900,600))
        self.text_widget = QtWidgets.QTextBrowser(self)

        self.text_widget.setOpenLinks(False)
        self.text_widget.setOpenExternalLinks(False)
        self.text_widget.anchorClicked.connect(self.on_anchor_clicked)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.text_widget)

    def on_anchor_clicked(self, link):
        slink = str(link.toString())
        if slink.find(self.QRC_TOKEN) == 0:
            items = slink.split('#')
            self.show(items[0].replace(self.QRC_TOKEN, ''))
            if len(items) > 1:
                self.text_widget.scrollToAnchor(items[1])
        elif slink.find('#') == 0:
            self.text_widget.scrollToAnchor(slink[1:])
        else:
            QtGui.QDesktopServices.openUrl(link)

    def load_qrc_text(self, name):
        file_name = ':%s' % name
        fp = QtCore.QFile(file_name)
        text = None
        if fp.open(QtCore.QIODevice.ReadOnly | QtCore.QIODevice.Text):
            stream = QtCore.QTextStream(fp)
            text = str(stream.readAll())
            fp.close()
        return text

    def show(self, name, link='_top', title=None, header='_header',
                  footer='_footer', html_text=None):
        self.text_widget.clear()

        # if no content was given try to load the context via the name
        if html_text is None:
            html_text = self.load_qrc_text('help/%s.html' %name.lower())

        if html_text is not None:
            css_text = self.load_qrc_text('help/help.css')

            if header is not None:
                header_text = self.load_qrc_text('help/%s.html' %header)
                if header_text is not None:
                    html_text = header_text + html_text

            if not footer is None:
                footer_text = self.load_qrc_text('help/%s.html' %footer)
                if footer_text is not None:
                    html_text = html_text + footer_text

            doc = QtGui.QTextDocument()
            if css_text is not None:
                doc.setDefaultStyleSheet(css_text)
            doc.setHtml(html_text)
            self.text_widget.setDocument(doc)

            if not link is None:
                self.text_widget.scrollToAnchor(link)
        else:
            self.text_widget.setHtml(("We are sorry, but help for '%s' "
                                      "was not found." %name))
        super(HelpBrowser, self).show()
        self.raise_()
