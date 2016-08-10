"""
                          The CellCognition Project
                  Copyright (c) 2006 - 2009 Michael Held
                   Gerlich Lab, ETH Zurich, Switzerland

           CellCognition is distributed under the LGPL License.
                     See trunk/LICENSE.txt for details.
               See trunk/AUTHORS.txt for author contributions.
"""
from __future__ import absolute_import
from __future__ import print_function
import six

__docformat__ = "epytext"
__author__ = 'Michael Held'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = ['Token',
           'TokenHandler',
           'TokenTemplate',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
import re
import string

#------------------------------------------------------------------------------
# extension module imports:
#


#------------------------------------------------------------------------------
# cecog imports:
#


#------------------------------------------------------------------------------
# constants:
#


#------------------------------------------------------------------------------
# functions:
#


#------------------------------------------------------------------------------
# classes:
#

class Token(object):

    def __init__(self, identifier, type_code='c', length='+', prefix='',
                 name=None, regex_type=None):
        format_length = length if length.isdigit() else '0'
        regex_length = '{%s}' % length if length.isdigit() else '%s' % length
        if type_code == 'i':
            format_string = '%%%s%sd'
            if regex_type is None:
                regex_type = '\d'
            regex_string = "%%s(?P<%%s>%s%%s)" % regex_type
            data_type = int
        else:
            format_string = '%%%s%ss'
            if regex_type is None:
                regex_type = '.'
            regex_string = "%%s(?P<%%s>%s%%s)" % regex_type
            data_type = str
        self.name = identifier if name is None else name
        self.identifier = identifier
        self.format = format_string % (prefix, format_length)
        self.regex = re.compile(regex_string % (self.identifier,
                                                self.name,
                                                regex_length))
        self.type = data_type


class TokenHandler(object):

    def __init__(self, separator=None):
        self._token = {}
        self.separator = separator

    def __str__(self):
        return '\n'.join(["token '%s': %s, %s, %s" % \
                          (t.name, t.format, t.regex.pattern, t.type)
                          for t in six.itervalues(self._token)])

    def register_token(self, token):
        self._token[token.name] = token

    def format_token(self, name, value):
        return '%s%s' % (name,  self._token[name].format % value)

    def has_token(self, name):
        return name in self._token

    def search(self, name, text):
        token = self._token[name]
        if self.separator is None:
            result = token.regex.search(text)
            if not result is None:
                result = token.type(result.group(1))
        else:
            for item in text.split(self.separator):
                result = token.regex.search(item)
                if not result is None:
                    result = token.type(result.group(1))
                    break
        return result

    def search_all(self, text):
        result = {}
        for name in six.iterkeys(self._token):
            result[name] = self.search(name, text)
        return result


class TokenTemplate(TokenHandler):

    def __init__(self):
        super(TokenTemplate, self).__init__()
        self._templates = {}

    def __str__(self):
        str1 = "%s\n\n" % super(TokenTemplate, self).__str__()
        str1 += "\n".join(["template '%s': %s" % (k, v.template)
                           for k,v, in six.iteritems(self._templates)])
        str1 += "\n"
        return str1

    def register_template(self, name, template):
        self._templates[name] = string.Template(template)

    def format_template(self, name, **mappings):
        mappings.update([(k, self.format_token(k, v))
                         for k,v in six.iteritems(mappings)
                         if self.has_token(k)])
        # FIXME
        return self._templates[name].substitute(mappings).replace('\.', '.')

    def has_template(self, name):
        return name in self._templates

    def generate_pattern(self, name, **mappings):
        mappings.update([(t.name, t.regex.pattern)
                         for t in six.itervalues(self._token)])
        return self._templates[name].substitute(mappings)

    def match(self, name, text, **mappings):
        regex = re.compile(self.generate_pattern(name, **mappings))
        match = regex.match(text)
        results = None
        if not match is None:
            results = match.groupdict()
            # convert types
            results.update([(k, self._token[k].type(v))
                           for k,v in six.iteritems(results)])
        return results


#------------------------------------------------------------------------------
# main:
#

if __name__ == "__main__":

    foo = TokenTemplate()

    foo.register_token(Token('P', type_code='i', length='4', prefix='0'))
    foo.register_token(Token('T', type_code='i', length='5', prefix='0'))
    foo.register_token(Token('O', type_code='i', length='4', prefix='0'))
    foo.register_token(Token('C', type_code='c', length='+', prefix=''))
    foo.register_token(Token('R', type_code='c', length='+', prefix=''))
    foo.register_token(Token('F', type_code='c', length='+', prefix=''))

    print(foo)

    foo.register_template('EVENT_FOLDER',
                         '${P}_${T}_${O}')
    foo.register_template('FEATURE_FILE',
                          '${prefix}__${P}__${T}__${O}__${C}__${R}\.${ext}')
    foo.register_template('FEATURE_PLOT',
                          '${T}__${O}__${C}__${R}__${F}.${ext}')
    foo.register_template('PLOT_TITLE',
                          '${C} ${R} ${feature}')
    foo.register_template('PLOT_FILE',
                          '${prefix}__${P}__${T}__${O}__${C}__${R}\.${ext}')

    print(foo)
