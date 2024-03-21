import abstractions.text as at
from pydantic import BaseModel

def safe_schema_draw(schema: BaseModel, out: str = 'schema.png'):
    try:
        import erdantic as erd
        erd.draw(schema, out = 'gang.png')
    except ImportError as e:
        print(e)
        print("erdantic not installed, good luck with pygraphviz and graphviz installations!")