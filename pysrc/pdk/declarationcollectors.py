"""
Classes for collecting declarations in class namespaces.

Declarations always have a declaration container name and a declarator class
specifying the name of the class attribute to use for looking up the
declaration definitions and the class to expect for each declaration.

It is also possible to put virtual declarations in the class namespace.
Virtual declarations are just placeholders, ensuring (at runtime) that this
declared entity has to be implemented in a derived class.

FOG 06.2006
"""

__docformat__ = "epytext"

__author__ = 'F Oliver Gathmann'
__date__ = '$Date$'
__revision__ = '$Rev$'
__source__ = '$URL::                                                          $'

__all__ = ['DeclarationCollector',
           'MetaDeclarationCollector',
           'get_declarations',
           'is_public',
           ]

#------------------------------------------------------------------------------
# standard library imports:
#
from copy import deepcopy

#------------------------------------------------------------------------------
# extension module imports:
#

#------------------------------------------------------------------------------
# pdk imports:
#
from pdk.pyutils import get_bases

#------------------------------------------------------------------------------
# constants:
#

#------------------------------------------------------------------------------
# classes:
#

class MetaDeclarationCollector(type):
    """
    Meta class for collecting and processing attribute declarations

    This meta class will collect all declarations held in the declaration
    container of the class being instantiated and all its base classes.
    A deep copy of the collected declaration container is then placed in
    the namespace of the derived class.

    The declaration container type can either be a C{list} or a C{dict}.
    """

    def __init__(mcs, name, bases, class_namespace):
        """
        Extends C{type.__init__}.

        Performs the collection of declarations in the given class and all
        its base classes and stores the (deepcopied) declarations in the
        class namespace.
        """
        try:
            decl_container_name = mcs.get_declaration_container_name()
        except NotImplementedError:
            pass
        else:
            decls = mcs._collect_declarations(decl_container_name)
            if not decls is None:
                setattr(mcs, decl_container_name, decls)
        super(MetaDeclarationCollector, mcs).__init__(name, bases,
                                                      class_namespace)

    #
    # public methods:
    #

    def get_declarations(mcs):
        """
        Returns the declaration container for this class (as it was collected
        by the constructor).

        @return: declaration container (a C{list} or a C{dict})
        """
        return getattr(mcs, mcs.get_declaration_container_name())

    #
    # protected methods:
    #

    def _collect_declarations(mcs, decl_container_name):
        """
        Traverses the inheritance tree of this class and builds up a
        declaration container from all the declarations found. Each
        declaration is then validated through the L{_validate_declaration}
        method.

        @param decl_container_name: declaration container name
        @type decl_container_name: string
        """
        decls = _get_declarations(mcs, decl_container_name)
        if not decls is None:
            if isinstance(decls, list):
                # convert the list to a set, overriding declarations from
                # lower in the tree with declarations from higher in the tree:
                for count in range(len(decls)):
                    decl = decls.pop()
                    if not decl in decls[:count]:
                        valid_decl = mcs._validate_declaration(decl)
                        decls.insert(0, valid_decl)
            elif isinstance(decls, dict):
                for key, decl in decls.items():
                    decls[key] = mcs._validate_declaration(decl)
        return decls

    def _validate_declaration(mcs, decl):
        """
        Validates the given declaration. This default implementation just
        ensures that the declaration is an instance of the class specified in
        the (virtual) C{DECLARATOR_CLASS} class attribute; if the given
        value is not already a declaration instance, it passes it to the
        declaration class constructor.

        @param decl: declaration to validate or arguments to be passed
          to the declaration class
        @type decl: object
        """
        # FIXME: drop support for auto-instantiation of declarations
        decl_class = mcs.get_declaration_class()
        if not isinstance(decl, decl_class):
            valid_decl = decl_class(decl)
        else:
            valid_decl = decl
        return valid_decl


class DeclarationCollector(object):
    """
    Base class for classes defining collections of declarations

    Use this as a base class to enable automatic declaration of declarations
    at class instantiation time by virtue of the
    L{MetaDeclarationCollector} meta class.
    """

    __metaclass__ = MetaDeclarationCollector

    #
    # public methods:
    #

    @classmethod
    def get_declaration_class(cls):
        """
        Returns the class object to use for declarations gathered by this
        collector.

        @return: declarator class (class object)
        """
        raise NotImplementedError('Abstract method.')

    @classmethod
    def get_declaration_container_name(cls):
        """
        Returns the name of the class attribute referring to the conainer
        that will hold the declarations to gather by this collector.

        @return: declaration container attribute name (string)
        """
        raise NotImplementedError('Abstract method.')


#------------------------------------------------------------------------------
# functions:
#

def _get_declarations(cls, container_name):
    """
    Returns the declarations from the given class and declaration container
    name.

    Note that this function manually traverses all base classes of the given
    class.

    @param cls: class do get the declarations for
    @type cls: type
    @param container_name: declaration container name
    @type container_name: string
    @return: a list or dictionary containing declarations or C{None}
    """
    decls = oExpectedType = None
    for oBaseClass in get_bases(cls) + [cls]:
        try:
            oContainer = getattr(oBaseClass, container_name)
        except AttributeError:
            continue
        else:
            if decls is None:
                # initialize the declarations container in the first pass
                # through the loop:
                decls = type(oContainer)()
                if not isinstance(oContainer, (list,dict)):
                    raise ValueError('invalid declaration container '
                                     'type "%s"' % type(oContainer))
                oExpectedType = type(oContainer)
            elif not isinstance(oContainer, oExpectedType):
                raise ValueError('invalid declaration container '
                                 'type "%s" (expected "%s")' %
                                 (type(oContainer), oExpectedType))
            if isinstance(oContainer, list):
                decls.extend([deepcopy(oDecl)
                               for oDecl in oContainer])
            elif isinstance(oContainer, dict):
                decls.update(dict([(key, deepcopy(oValue))
                                   for (key, oValue) in oContainer.items() ]
                                   )
                              )
    return decls


def is_public(identifier):
    """
    Checks if the given identifier is public.

    @param identifier: identifier to check
    @type identifier: string
    @return: Boolean
    """
    return not identifier.startswith('_')


def get_declarations(cls, container_name):
    """
    Returns a list of all declarations in the given class held in the
    specified container (specified as a class attribute name).

    Unless L{cls} inherits from L{DeclarationCollector}, this will traverse
    all base classes of L{cls}. Returns C{None} if none of the base classes
    nor the class L{cls} has declared any attributes in a container of the
    specified name.

    @param cls: class to collect declarations of
    @type cls: arbitrary type object
    @param container_name: name of the declaration container attribute
    @type container_name: string
    """
    if issubclass(cls, DeclarationCollector) \
           and container_name == cls.get_declaration_container_name():
        decls = cls.get_declarations()
    else:
        decls = _get_declarations(cls, container_name)
    return decls
