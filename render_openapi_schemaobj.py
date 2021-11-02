import jinja2
import re
import mkdocs.plugins
from pathlib import Path
import yaml


USAGE_MSG = ("Usage: '@@render <filename>@@' ")

TOKEN=re.compile("@@render_schema\s+(?P<path>[A-Za-z0-9\-\/\._]+)\s*@@")
ERROR_TEMPLATE = jinja2.Template("!! RENDER_SCHEMA ERROR: {{error}} !!")

TEMPLATE_ENUMS=jinja2.Template("""
<div class="data-model">
<ul>
    <li><b>Description:</b> {{schema_obj.description}}</li>
    <li><b>Type</b>: {{schema_obj.type}}</li> 
    <li><b>Enum</b>: {{enums}}
</ul>
</div>
""")

TEMPLATE_OBJECT_MODEL=jinja2.Template("""
<div class="data-model">
<ul>
    <li><b>Description:</b> {{schema_obj.description}}</li>
    <li><b>Type</b>: {{schema_obj.type}}</li> 
<table border="1">
<tr>
    <th>Property</th>
    <th>Type</th>
    <th>Description</th>
</tr>
{% for p in properties %}
<TR>
   <TD class="pname"><SPAN>{{p.name}}</SPAN></TD>
   <TD class="ptype"><SPAN>{{p.ptype}}</SPAN></TD>
   <TD class="description"><SPAN>{{p.description}}</SPAN></TD>
</TR>
{% endfor %}
</table>
</div>
""")

class SchemaObjProperty:
    def __init__(self, name, schemaObj):
        """
        schemaObj: Corresponds to dictionary corresponding to 
            https://github.com/OAI/OpenAPI-Specification/blob/main/schemas/v3.0/schema.yaml#/definitions/Schema
        """
        self.name = name
        self.description = ""
        if "description" in schemaObj:
            self.description = schemaObj['description']
            
        print(schemaObj)

        if '$ref' in schemaObj:
            self.ptype = "referenceObj"
            typename = schemaObj['$ref'].split('/')[-1]
            self.ptype_str = f'<a href="#{typename}">{typename}</a>'
        elif 'oneOf' in schemaObj:
            self.ptype = "oneOf"
            self.ptype_str = "oneOf: <br> <ul>"
            for value in schemaObj['oneOf']:
                typename = value['$ref'].split('/')[-1]
                self.ptype_str += f'<li><a href="#{typename}">{typename}</a></li>'
            self.ptype_str += "</ul>"
        elif 'type' in  schemaObj and (schemaObj['type'] == 'array'):
            if 'type' in schemaObj['items']:
                item_type = schemaObj['items']['type']
                self.ptype_str = f"array({item_type})"
            elif '$ref' in schemaObj['items']:
                item_type = schemaObj['items']['$ref'].split('/')[-1]
                self.ptype_str = f'<li>array(<a href="#{item_type}">{item_type}</a>)</li>'
        elif 'type' in schemaObj:
            self.ptype = schemaObj['type']
            self.ptype_str = schemaObj['type']
        else:
            raise Exception(f"Property {name} is noneof ['$ref', 'oneOf', 'array'] or any other basic type")

    def get_property_type(self):
        return self.ptype_str

    def get_name(self):
        return self.name

    def get_description(self):
        return self.description




class SchemaRenderPlugin(mkdocs.plugins.BasePlugin):
    def render_schema_dict(schema_dict):
        schema_desc_records = []
        html_tables = ""
        for sname, v in schema_dict['definitions'].items():
            schema_obj = {}
            if 'description' in v:
                schema_obj['description'] = v['description']
            else:
                schema_obj['description'] = ""
            schema_obj['type']  = v['type']
            
            if ('type' in v) and v['type'] == 'object':
                
                for pname, pval in schema_dict['definitions'][sname]['properties'].items():
                    try:    
                        sop = SchemaObjProperty(pname, pval)
                        schema_desc_records.append(dict(
                            name=sop.get_name(),
                            ptype=sop.get_property_type(),
                            description=sop.get_description()
                        ))
                    except Exception as e:
                        raise Exception(f"Error while processing {pname} <br>" + str(e))
                rendered_type = TEMPLATE_OBJECT_MODEL.render(properties=schema_desc_records, schema_obj=schema_obj)
            elif 'enum' in v:
                if 'type' in v:
                    ptype = f"enum({v['type']} <br> {v['enum']}"
                    description = v['description'] if 'description' in v else ""
                    schema_desc_records.append(dict(
                            name=sname,
                            ptype=ptype,
                            description=description
                        ))
                    rendered_type = TEMPLATE_ENUMS.render(schema_obj=schema_obj, enums=v['enum'])
                else:
                    raise Exception(f"type not defined for enum")
            html_tables += rendered_type
            
        return html_tables

    def on_page_markdown(self, markdown, page, config, files):
        print(page.file.abs_src_path)

        match = TOKEN.search(markdown)
        
        if match is None:
            return markdown

        pre_token = markdown[:match.start()]
        post_token = markdown[match.end():]

        def _error(message):
            return (pre_token + ERROR_TEMPLATE.render(error=message) +
                    post_token)

        path = match.group("path")

        if path is None:
            return _error(USAGE_MSG)

        print(path)
        schema_obj_path = Path(page.file.abs_src_path).parent.joinpath(path).resolve()
        print(schema_obj_path)
        with schema_obj_path.open() as f:
            schema_data = f.read()
            schema_dict = yaml.safe_load(schema_data)
            print(schema_dict)

            try:
                html_tables = SchemaRenderPlugin.render_schema_dict(schema_dict)
            except Exception as e:
                return _error(str(e))

            markdown = pre_token + html_tables + post_token

        # If multiple render_schema exist.
        return self.on_page_markdown(markdown, page, config, files)

if __name__ == '__main__':
    import unittest
    class TestScemaObjRender(unittest.TestCase):
        def test_case_1(self):
            schema_1 = """
            $ref: '#/definitions/mc_params'
            definitions:
                mc_params:
                    properties:
                        container_type:
                            $ref: 'media_container_enum.yaml#/definitions/media_container_enum'
                        container_params:
                            oneOf:
                                - $ref: 'm3u8_params.yaml#/definitions/m3u8_params'
                                - $ref: 'm2ts_params.yaml#/definitions/m2ts_params'
                            description: Parameters for the specific media container format e.g. m2ts, mp4m m2u8 etc
                    additionalProperties: false
                    description: Parameters describing media container 
                    type: object
            """
            schema_dict = yaml.safe_load(schema_1)
            html_tables = SchemaRenderPlugin.render_schema_dict(schema_dict)
            with open('test_case_1.html', 'w') as fd:
                fd.write(html_tables)

        def test_case_2(self):
            schema_2 = """
            $ref: '#/definitions/m3u8_params'
            definitions:
                m3u8_params:
                    properties:
                        video_pid:
                            type: integer
                        audio_pids:
                            items: 
                                type: integer
                            type: array
                        segment_duration:
                            type: integer
                            description: Segment duration in seconds
                    type: object
                    description: M3U8 specific parameters
            """
            schema_dict = yaml.safe_load(schema_2)
            html_tables = SchemaRenderPlugin.render_schema_dict(schema_dict)
            with open('test_case_2.html', 'w') as fd:
                fd.write(html_tables)

        def test_case_3(self):
            schema_3 = """
            $ref: '#/definitions/media_container_enum'
            definitions:
                media_container_enum:
                    enum:
                        - M2TS
                        - M3U8
                        - MOV
                        - MP4 
                        - MXF
                        - WEBM
                    type: string
                    description: Media container types
            """
            schema_dict = yaml.safe_load(schema_3)
            html_tables = SchemaRenderPlugin.render_schema_dict(schema_dict)
            with open('test_case_3.html', 'w') as fd:
                fd.write(html_tables)

        def test_case_4(self):
            schema_4 = """
$schema: http://json-schema.org/draft-04/schema#
$ref: '#/definitions/recorder'
definitions:
  recorder:
    properties:
      recorder_id:
        type: PUNIQID16
        description: <a href=key_type_definitions.html#puniqid16>Typedef PUNIQID16</a>. A UUID with "rec" prefix.
      recorder_name:
        type: string
      recorder_status:
        enum:
          - IDLE 
          - STARTING
          - ACTIVE
          - STOPPING
        type: string
        description: <a href=key_type_definitions.html#standard_status>Typedef STANDARD_STATUS</a>. 
      account_id:
        type: string
        description: A unique id representing the user account. <a href=key_type_definitions.html#uniqid16>Typedef UNIQID16</a>
      created_date:
        type: string
        description: ISO8601 date-time when the recorder representation was created. <a href=key_type_definitions.html#iso8601>Typedef ISO8601</a>
      start_time:
        type: string
        description: ISO8601 date-time when the recorder resources are provisioned and the recording is started. <a href=key_type_definitions.html#iso8601>Typedef ISO8601</a>
      duration_sec:
        type: integer
        description: Recording duration in seconds
      recorder_segmentation_policy:
        $ref: 'recorder_segmentation_policy.yaml##/definitions/recorder_segmentation_policy'
      recorder_media_descriptions:
        items:
          $ref: 'media_info_params.yaml#/definitions/media_info_params'
        type: array
      recorder_media_outputs:
        items:
          type: string
          description: A URL location where the recordings can be accessed. E.g. http://compass.amagi.tv/api/v1/storage/recordings/123456
        type: array
    additionalProperties: false
    type: object
            """
            schema_dict = yaml.safe_load(schema_4)
            html_tables = SchemaRenderPlugin.render_schema_dict(schema_dict)
            with open('test_case_3.html', 'w') as fd:
                fd.write(html_tables)
    unittest.main()
