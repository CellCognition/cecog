"""
gen_template.py

Generate a template of a Qt help page.

The script scans all html files, generates a table of contents setups all
keywords for the index search and all files to the resource list. The output
file is only a template. Keywords must be changed manually.
"""
from __future__ import absolute_import
from __future__ import print_function

__author__ = 'rudolf.hoefler@gmail.com'


import sys
import os

import argparse
import mimetypes

# keywords = list()
# lines = open(sys.argv[1]).readlines()
# for line in lines:
#     if "<a name=" in line:
#         anchor = line.split("name=")[1].split('"')[1]
#         print """<keyword name="XXX" ref="%s#%s"/>""" %(sys.argv[1], anchor)


class TemplateGenerator(object):

    def __init__(self, directory, output):

        self.html_files = list()
        self.image_files = list()
        self.css_files= list()

        for root, dirs, files in os.walk(directory):
            for file_ in files:
                path = os.path.join(root, file_)
                if mimetypes.guess_type(path)[0] == mimetypes.types_map[".html"]:
                    self.html_files.append(path)
                elif mimetypes.guess_type(path)[0] == mimetypes.types_map[".png"]:
                    self.image_files.append(path)
                elif mimetypes.guess_type(path)[0] == mimetypes.types_map[".css"]:
                    self.css_files.append(path)


        print(self.genFileList())
        print(self.genKeyWords())

    def genFileList(self):

        txt = list()
        for file_ in self.css_files + self.html_files + self.image_files:
            txt.append("""<file>%s</file>""" %file_)
        return "\n".join(txt)

    def genKeyWords(self):
        keywords = list()
        for html_file in self.html_files:
            lines = open(html_file).readlines()
            for line in lines:
                if "<a name=" in line:
                    anchor = line.split("name=")[1].split('"')[1]
                    keywords.append("""<keyword name="XXX" ref="%s#%s"/>""" %(html_file, anchor))
        return "\n".join(keywords)




if __name__ == "__main__":

    parser = argparse.ArgumentParser( \
        description='Auto generate a qt-qhp')
    parser.add_argument('directory', help=('Directory containing all for '
                                           'documentation necessary files'))

    parser.add_argument('-o', '--output', help="Ouput template (*.qhp)",
                        default="template.qhp")
    args = parser.parse_args()

    TemplateGenerator(args.directory, args.output)
