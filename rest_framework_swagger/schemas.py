from rest_framework.compat import urlparse
from rest_framework.schemas import SchemaGenerator as SchemaGenerator

from .document import Link, Response, Schema, Property


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
        class Dummy(object):
            pass
        responses = []
        meta = getattr(view, 'Meta', Dummy)
        swagger_responses = getattr(meta, 'swagger_responses', {})
        action = swagger_responses.get(view.action, {})
        for state, response in action.items():
            description = response.get('description', '')
            schema = self._generate_schema_from_dict(response.get('schema', {}))
            responses.append(Response(state, description, schema))
        return responses

    def _generate_schema_from_dict(self, schema_dict):
        properties = self._generate_properties_list_from_dict(schema_dict.get('properties', {}))
        ref_name = schema_dict.get('ref_name', None)
        print(ref_name)
        if schema_dict.get('items', None):
            items = self._generate_schema_from_dict(schema_dict.get('items'))
        else:
            items = None
        return Schema(schema_dict.get('type'), ref_name, properties, items)

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
