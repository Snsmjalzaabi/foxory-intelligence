"""Small-format parsing shared by the application and sealed worker; stdlib only."""
import csv
import io
import json
from pathlib import Path
TEXT_EXTENSIONS={'.txt','.md','.csv','.json'}

def extract_text(name:str,raw:bytes)->str:
    extension=Path(name).suffix.lower()
    if extension not in TEXT_EXTENSIONS:raise ValueError('Unsupported text format')
    text=raw.decode('utf-8-sig')
    if '\x00' in text:raise ValueError('Binary content rejected')
    if len(text)>2_000_000:raise ValueError('Extracted text limit exceeded')
    if extension=='.json':json.loads(text)
    if extension=='.csv':
        for _ in csv.reader(io.StringIO(text)):pass
    return text
