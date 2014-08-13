"""
xmlserializer.py
"""

__author__ = 'rudolf.hoefler@gmail.com'
__licence__ = 'LGPL'


__all__ = ('XmlSerializer', )


import re
from lxml import etree
from collections import OrderedDict


types = {float: float.__name__,
         int: int.__name__,
         long: long.__name__,
         str: str.__name__,
         complex: complex.__name__,
         unicode: unicode.__name__,
         list: list.__name__,
         tuple: tuple.__name__,
         dict: dict.__name__,
         OrderedDict: OrderedDict.__name__,
         bool: bool.__name__,
         None: type(None).__name__,
         set: set.__name__,
         frozenset: frozenset.__name__}

def key2tag(key):
    return "__%s" %key

def tag2key(tag):
    return tag[2:]


class XmlMetaSerializer(type):
    """Metaclass to 'register' all derived child classes."""

    def __init__(cls, name, bases, dct):

        if len(cls.__mro__) == 2:
            setattr(cls , "_classes", {})
        elif len(cls.__mro__)  >= 3:
            bases[0]._classes[name] = cls
            return type.__init__(cls, name, bases, dct)


class XmlSerializer(object):
    """Parenet for all serializable objects"""

    __metaclass__ = XmlMetaSerializer
    _TYPE = 'type'

    def __init__(self, *args, **kw):
        super(XmlSerializer, self).__init__()

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def _validate(self, name):

        if not isinstance(name, basestring):
            raise TypeError('tag names must be string not %s' %type(name))

        if re.match('^(?!xml)[A-Za-z_][A-Za-z0-9._:]*$', name) is None:
            raise ValueError('%s is not a valid xml name' %name)

    def _toText(self, value):

        if isinstance(value, (list, tuple, set, frozenset)):
            return " ".join([str(v) for v in value])
        elif isinstance(value, bool):
            # booleans to lower case to be xml conform
            return str(value).lower()
        else:
            return str(value)

    def _dict2etree(self, tag, dict_):
        element = etree.Element(tag)
        element.attrib[self._TYPE] = type(dict_).__name__
        for key_, value in dict_.iteritems():
            key =  key2tag(key_)
            self._validate(key)
            if isinstance(value, dict):
                element.append(self._dict2etree(key, value))
            else:
                child = etree.SubElement(element, key)
                child.attrib[self._TYPE] = type(value).__name__
                child.text = self._toText(value)
        return element

    def to_xml(self, name=None):
        if name is None:
            name = self.__class__.__name__

        root = etree.Element(name)
        root.attrib['type'] = type(self).__name__

        for key, value in self.__dict__.iteritems():
            self._validate(key)

            if isinstance(value, dict):
                root.append(self._dict2etree(key, value))
            elif value.__class__.__name__ in self._classes:
                root.append(value.to_xml(key))
            else:
                child = etree.SubElement(root, key)
                child.attrib[self._TYPE] = type(value).__name__
                child.text = self._toText(value)

        return root

    def serialize(self, pretty_print=True):
        root = self.to_xml()
        return etree.tostring(root, pretty_print=pretty_print)

    @classmethod
    def deserialize(cls, string):
        root = etree.fromstring(string)
        obj = cls._classes[root.tag]()
        obj.load(string)
        return obj

    def load(self, root):
        if isinstance(root, basestring):
            root = etree.fromstring(root)

        for child in root.getchildren():
            print child.tag
            self.__dict__[child.tag] = self._to_attr(child)

    def _to_seq(self, string):
        print string
        try:
            return [eval(v) for v in string.split()]
        except (NameError, SyntaxError):
            return [v for v in string.split()]

    def _to_attr(self, element):
        _type = element.attrib[self._TYPE]
        if _type in (types[int], types[float], types[long], types[complex]):
            return eval(element.text)
        elif _type == types[bool]:
            return eval(element.text.title())
        elif _type in (types[str], types[unicode]):
            return element.text
        elif _type == types[list]:
            return self._to_seq(element.text)
        elif _type == types[tuple]:
            return tuple(self._to_seq(element.text))
        elif _type == types[set]:
            return set(self._to_seq(element.text))
        elif _type == types[frozenset]:
            return frozenset(self._to_seq(element.text))
        elif _type in (types[dict], types[OrderedDict]):
            return self._etree2dict(element)
        elif _type in self._classes:
            inst = self._classes[_type]()
            inst.load(element)
            return inst
        elif _type == types[None]:
            return None
        else:
            raise RuntimeError('cannot deserialize %s' %_type)

    def _etree2dict(self, element):
        edict = {}
        for child in element.getchildren():
            edict[tag2key(child.tag)] = self._to_attr(child)
        return edict
