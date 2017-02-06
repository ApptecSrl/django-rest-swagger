import itypes
from coreapi import Link as CoreLink
from coreapi.codecs.display import _fields_to_plaintext
from coreapi.codecs.python import _to_repr
from coreapi.compat import console_style
from coreapi.compat import string_types
from collections import namedtuple


def _colorize_keys(text):
    return console_style(text, fg='cyan')  # pragma: nocover


Property = namedtuple('Property', ['name', 'type', 'format', 'description'])


class Schema(itypes.Object):

    def __init__(self, var_type=None, ref_name=None, properties=None, items=None):

        if var_type is not None and not isinstance(var_type, string_types):
            raise TypeError("'var_type' must be a string.")
        if ref_name is not None and not isinstance(ref_name, string_types):
            raise TypeError("'ref_name' must be a string.")
        if (properties is not None) and (not isinstance(properties, (list, tuple))):
            raise TypeError("Argument 'properties' must be a list.")
        if (properties is not None) and any([
            not (isinstance(item, string_types) or isinstance(item, Property))
            for item in properties
        ]):
            raise TypeError("Argument 'properties' must be a list of strings or properties.")
        if items is not None and not isinstance(items, Schema):
            raise TypeError("'items' must be a Schema.")

        self._var_type = '' if (var_type is None) else var_type
        self._ref_name = '' if (ref_name is None) else ref_name
        self._properties = () if (properties is None) else properties
        self._items = items

    @property
    def type(self):
        return self._var_type

    @property
    def ref_name(self):
        return self._ref_name

    @property
    def properties(self):
        return self._properties

    @property
    def items(self):
        return self._items

    def __repr__(self):
        args = "type=%s" % self.type
        # args += ", ref_name=%s" % self.ref_name
        if self.properties:
            repr_proprieties = ', '.join([prop.name for prop in self.properties])
            args += "properties=[%s]" % repr_proprieties
        if self.items:
            args += ", items=%s" % repr(self.items)
        return "Schema(%s)" % args

    def __str__(self):
        return self.__repr__


class Response(itypes.Object):

    def __init__(self, state, description, schema=None):
        if not isinstance(state, string_types):
            raise TypeError("Argument 'state' must be a string.")
        if not isinstance(description, string_types):
            raise TypeError("Argument 'description' must be a string.")
        if (schema is not None) and (not isinstance(schema, Schema)):
            raise TypeError("Argument 'schema' must be a Schema.")

        self._state = state
        self._description = description
        self._schema = schema

    @property
    def state(self):
        return self._state

    @property
    def description(self):
        return self._description

    @property
    def schema(self):
        return self._schema

    def __repr__(self):
        args = "state=%s" % repr(self.state)
        args += ", description=%s" % repr(self.description)
        if self.schema:
            args += ", schema=%s" % repr(self.schema)
        return "Response(%s)" % args

    def __str__(self):
        return repr(self)


class Link(CoreLink):

    def __init__(self, url=None, action=None, encoding=None, transform=None, title=None, description=None, fields=None,
                 responses=None):

        super(Link, self).__init__(url, action, encoding, transform, title, description, fields)

        if (responses is not None) and any([
            not isinstance(item, Response)
            for item in responses
        ]):
            raise TypeError("Argument 'responses' must be a list of responses.")

        self._responses = () if (responses is None) else tuple([
            item for item in responses
        ])

    @property
    def responses(self):
        return self._responses

    def __repr__(self):
        args = "url=%s" % repr(self.url)
        if self.action:
            args += ", action=%s" % repr(self.action)
        if self.encoding:
            args += ", encoding=%s" % repr(self.encoding)
        if self.transform:
            args += ", transform=%s" % repr(self.transform)
        if self.description:
            args += ", description=%s" % repr(self.description)
        if self.fields:
            fields_repr = ', '.join(_to_repr(item) for item in self.fields)
            args += ", fields=[%s]" % fields_repr
        if self.responses:
            responses_repr = ', '.join(_to_repr(item) for item in self.responses)
            args += ", responses=[%s]" % responses_repr
        return "Link(%s)" % args

    def __str__(self):
        return (
            'link(' +
            _fields_to_plaintext(self, colorize=False) +
            ')'
        )
