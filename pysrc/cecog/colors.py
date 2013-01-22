"""
colors.py

Defines some colors and mappings
"""

__author__ = 'rudolf.hoefler@gmail.com'
__copyright__ = ('The CellCognition Project'
                 'Copyright (c) 2006 - 2012'
                 'Gerlich Lab, IMBA Vienna, Austria'
                 'see AUTHORS.txt for contributions')
__licence__ = 'LGPL'
__url__ = 'www.cellcognition.org'


class Colors(object):

    red = '#FF0000'
    green = '#00FF00'
    blue = '#0000FF'
    yellow = '#FFFF00'
    magenta ='#FF00FF'
    cyan = '#00FFFF'
    white = '#FFFFFF'

    colors = ['white', 'red', 'green', 'blue', 'yellow', 'magenta', 'cyan']

    channel_table = {'rfp': 'red',
                     'gfp': 'green',
                     'yfp': 'yellow',
                     'cfp': 'cyan'}

    @classmethod
    def channel_color(cls, name):
        if name not in cls.channel_table.keys():
            raise AttributeError('no channel_color defined')

        return cls.channel_table[name]

    @classmethod
    def channel_hexcolor(cls, name):
        if name not in cls.channel_table.keys():
            raise AttributeError('no channel_color (%s) defined' %name)

        return getattr(cls, cls.channel_table[name])


if __name__ == "__main__":
    print 'by attribute:', Colors.red
    print 'colors: ', Colors.colors
    print 'channel color: ', Colors.channel_color('rfp')
    print 'color table: ', dict((c, getattr(Colors, c)) for c in Colors.colors)
