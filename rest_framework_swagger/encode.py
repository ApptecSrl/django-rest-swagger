from collections import OrderedDict
from coreapi.compat import urlparse
from openapi_codec.utils import get_method, get_encoding, get_location, get_links_from_document


def generate_swagger_object(document):
    """
    Generates root of the Swagger spec.
    """
    parsed_url = urlparse.urlparse(document.url)

    swagger = OrderedDict()

    swagger['swagger'] = '2.0'
    swagger['info'] = OrderedDict()
    swagger['info']['title'] = document.title
    swagger['info']['version'] = ''  # Required by the spec

    if parsed_url.netloc:
        swagger['host'] = parsed_url.netloc
    if parsed_url.scheme:
        swagger['schemes'] = [parsed_url.scheme]

    swagger['paths'] = _get_paths_object(document)
    swagger['definitions'] = _get_definitions_object(document)

    return swagger


def _add_tag_prefix(item):
    operation_id, link, tags = item
    if tags:
        operation_id = tags[0] + '_' + operation_id
    return (operation_id, link, tags)


def _get_links(document):
    """
    Return a list of (operation_id, link, [tags])
    """
    # Extract all the links from the first or second level of the document.
    links = []
    for keys, link in get_links_from_document(document):
        if len(keys) > 1:
            operation_id = '_'.join(keys[1:])
            tags = [keys[0]]
        else:
            operation_id = keys[0]
            tags = []
        links.append((operation_id, link, tags))

    # Determine if the operation ids each have unique names or not.
    operation_ids = [item[0] for item in links]
    unique = len(set(operation_ids)) == len(links)

    # If the operation ids are not unique, then prefix them with the tag.
    if not unique:
        return [_add_tag_prefix(item) for item in links]

    return links


def _get_paths_object(document):
    paths = OrderedDict()

    links = _get_links(document)

    for operation_id, link, tags in links:
        if link.url not in paths:
            paths[link.url] = OrderedDict()

        method = get_method(link)
        operation = _get_operation(operation_id, link, tags)
        paths[link.url].update({method: operation})

    return paths


def _get_operation(operation_id, link, tags):
    encoding = get_encoding(link)
    description = link.description.strip()
    summary = description.splitlines()[0] if description else None

    operation = {
        'operationId': operation_id,
        'responses': _get_responses(link),
        'parameters': _get_parameters(link, encoding)
    }

    if description:
        operation['description'] = description
    if summary:
        operation['summary'] = summary
    if encoding:
        operation['consumes'] = [encoding]
    if tags:
        operation['tags'] = tags
    return operation


def _get_parameters(link, encoding):
    """
    Generates Swagger Parameter Item object.
    """
    parameters = []
    properties = {}
    required = []

    for field in link.fields:
        location = get_location(link, field)
        if location == 'form':
            if encoding in ('multipart/form-data', 'application/x-www-form-urlencoded'):
                # 'formData' in swagger MUST be one of these media types.
                parameter = {
                    'name': field.name,
                    'required': field.required,
                    'in': 'formData',
                    'description': field.description,
                    'type': field.type or 'string',
                }
                if field.type == 'array':
                    parameter['items'] = {'type': 'string'}
                parameters.append(parameter)
            else:
                # Expand coreapi fields with location='form' into a single swagger
                # parameter, with a schema containing multiple properties.
                use_type = field.type or 'string'
                if use_type == 'file':
                    use_type = 'string'

                schema_property = {
                    'description': field.description,
                    'type': use_type,
                }
                if field.type == 'array':
                    schema_property['items'] = {'type': 'string'}
                properties[field.name] = schema_property
                if field.required:
                    required.append(field.name)
        elif location == 'body':
            if encoding == 'application/octet-stream':
                # https://github.com/OAI/OpenAPI-Specification/issues/50#issuecomment-112063782
                schema = {'type': 'string', 'format': 'binary'}
            else:
                schema = {}
            parameter = {
                'name': field.name,
                'required': field.required,
                'in': location,
                'description': field.description,
                'schema': schema
            }
            parameters.append(parameter)
        else:
            parameter = {
                'name': field.name,
                'required': field.required,
                'in': location,
                'description': field.description,
                'type': field.type or 'string',
            }
            if field.type == 'array':
                parameter['items'] = {'type': 'string'}
            parameters.append(parameter)

    if properties:
        parameter = {
            'name': 'data',
            'in': 'body',
            'schema': {
                'type': 'object',
                'properties': properties
            }
        }
        if required:
            parameter['schema']['required'] = required
        parameters.append(parameter)

    return parameters


def _get_responses(link):
    """
    Returns minimally acceptable responses object based
    on action / method type.
    """
    responses = OrderedDict()
    if link.responses:
        for response in link.responses:
            responses.update(_format_response(response))

    template = {'description': ''}
    if link.action.lower() == 'post':
        if '201' not in responses.keys():
            responses['201'] = template
    elif link.action.lower() == 'delete':
        if '204' not in responses.keys():
            responses['204'] = template
    else:
        if '200' not in responses.keys():
            responses['200'] = template

    return responses


def _format_response(response):
    attributes = {'description': response.description}
    if response.schema:
        attributes['schema'] = _encode_schema(response.schema)
    return {response.state: attributes}


def _encode_schema(schema, definition=False):
    if schema.ref_name and not definition:
        return {'$ref': '#/definitions/%s' % schema.ref_name}

    encoded = OrderedDict()
    encoded['type'] = schema.type
    if schema.type == 'object':
        properties = {}
        for prop in schema.properties:
            item = {}
            if prop.type:
                item['type'] = prop.type
            if prop.format:
                item['format'] = prop.format
            if prop.description:
                item['description'] = prop.description
            properties[prop.name] = item
        encoded['properties'] = properties
    elif schema.type == 'array':
        if schema.items:
            encoded['items'] = _encode_schema(schema.items)

    return encoded


def _get_schema_definition(schema):
    name = None
    definition = {}
    if schema.ref_name:
        name = schema.ref_name
        definition = _encode_schema(schema, True)
    return name, definition


def _schema_walker(schema):
    definitions = OrderedDict()
    name, definition = _get_schema_definition(schema)
    if name:
        definitions[name] = definition
    if schema.items:
        depth_definitions = _schema_walker(schema.items)
        for k, v in depth_definitions.items():
            definitions[k] = v
    return definitions


def _get_definitions_object(document):
    definitions = OrderedDict()

    links = _get_links(document)

    for operation_id, link, tags in links:
        for response in link.responses:
            schema = response.schema
            if schema:
                schema_defs = _schema_walker(schema)
            for k, v in schema_defs.items():
                definitions[k] = v
    return definitions
