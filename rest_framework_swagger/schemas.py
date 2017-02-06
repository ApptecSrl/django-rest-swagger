from django.utils.encoding import force_text
from rest_framework.compat import urlparse
from rest_framework.schemas import SchemaGenerator
from rest_framework.schemas import types_lookup

from .document import Link, Response, Schema, Property


class Dummy(object):
    pass


class SwaggerSchemaGenerator(SchemaGenerator):

    def get_link(self, path, method, view):
        """
        Return a custom `Link` instance for the given endpoint.
        """
        fields = self.get_path_fields(path, method, view)
        fields += self.get_serializer_fields(path, method, view)
        fields += self.get_pagination_fields(path, method, view)
        fields += self.get_filter_fields(path, method, view)

        if fields and any([field.location in ('form', 'body') for field in fields]):
            encoding = self.get_encoding(path, method, view)
        else:
            encoding = None

        description = self.get_description(path, method, view)

        if self.url and path.startswith('/'):
            path = path[1:]

        responses = self.get_meta_responses(path, method, view)

        link = Link(
            url=urlparse.urljoin(self.url, path),
            action=method.lower(),
            encoding=encoding,
            fields=fields,
            description=description,
            responses=responses
        )
        return link

    def get_meta_responses(self, path, method, view):
        responses = []
        meta = getattr(view, 'Meta', Dummy)
        swagger_responses = getattr(meta, 'swagger_responses', {})
        action = swagger_responses.get(view.action, {})
        for state, response in action.items():
            description = response.get('description', '')
            schema = self._schema_parser(response.get('schema', {}))
            responses.append(Response(state, description, schema))
        return responses

    def _schema_parser(self, schema):
        ref_name = self.get_schema_reference(schema)
        if schema.get('properties'):
            properties = self._generate_properties_list_from_dict(schema.get('properties'))
        elif schema.get('serializer'):
            properties = self.get_serializer_proprieties(schema.get('serializer'))

        else:
            properties = []

        if schema.get('items', None):
            items = self._schema_parser(schema.get('items'))
        else:
            items = None
        return Schema(schema.get('type'), ref_name, properties, items)

    def get_schema_reference(self, schema):
        ref_name = schema.get('ref_name', None)
        if not ref_name:
            serializer = schema.get('serializer', None)
            if serializer:
                meta = getattr(serializer, 'Meta', Dummy)
                model = getattr(meta, 'model', None)
                if model:
                    ref_name = model.__name__
        return ref_name

    def get_serializer_proprieties(self, serializer):
        properties = []
        for field in serializer().fields.values():
            description = force_text(field.help_text) if field.help_text else ''
            prop = Property(
                name=field.field_name,
                type=types_lookup[field],
                format='',
                description=description
            )

            properties.append(prop)
        return properties

    def _generate_properties_list_from_dict(self, properties_dict_struct):
        properties = []
        for name, attributes in properties_dict_struct.items():
            properties.append(
                Property(
                    name,
                    attributes.get('type', ''),
                    attributes.get('format', ''),
                    attributes.get('description', '')
                )
            )
        return properties
