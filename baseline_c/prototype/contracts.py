"""Small validator for the JSON Schema keywords used in this package; no external dependencies."""
import json
from pathlib import Path

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / 'schemas/prototype.schema.json').read_text())

def validate_shape(value, schema=SCHEMA, path='case'):
    errors=[]
    # Decimal fields have a dedicated validator which retains E_UNKNOWN/E_DECIMAL.
    if path.endswith('.value'): return errors
    types=schema.get('type',[]);types=[types] if isinstance(types,str) else types
    matches={'null':value is None,'object':isinstance(value,dict),'array':isinstance(value,list),
             'boolean':type(value) is bool,'integer':type(value) is int,
             'number':type(value) in (int,float),'string':isinstance(value,str)}
    if types and not any(matches[t] for t in types):return [path+': wrong JSON type']
    if value is None:return errors
    if 'enum' in schema and value not in schema['enum']:errors.append(path+': unsupported value')
    if isinstance(value,dict):
        props=schema.get('properties',{})
        errors.extend(path+': missing '+k for k in schema.get('required',[]) if k not in value)
        if schema.get('additionalProperties') is False:errors.extend(path+': unexpected '+k for k in value if k not in props)
        for k,v in value.items():
            if k in props:errors.extend(validate_shape(v,props[k],path+'.'+k))
    if isinstance(value,list):
        for i,v in enumerate(value):errors.extend(validate_shape(v,schema.get('items',{}),path+f'[{i}]'))
    return errors
