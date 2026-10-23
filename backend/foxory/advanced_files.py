"""Bounded deterministic data operations and inert source archives; never executes code."""
import csv
import io
import json
import math
import statistics
import zipfile
from pathlib import PurePosixPath
from html import escape
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class SourceProject(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=200)
    files: dict[str, str] = Field(min_length=1, max_length=50)

    @model_validator(mode='after')
    def boundaries(self):
        total = 0
        for name, content in self.files.items():
            path = PurePosixPath(name)
            if (len(name)>180 or not name.isascii() or '\\' in name or ':' in name
                    or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./-' for c in name)
                    or path.is_absolute() or any(p in ('', '.', '..') for p in name.split('/'))
                    or any(p.lower() in ('.git', '.env') for p in path.parts)):
                raise ValueError('Unsafe project path')
            if '\x00' in content: raise ValueError('Binary content is unsupported')
            total += len(content.encode('utf-8'))
        if total > 20000: raise ValueError('Project source budget exceeded')
        return self

class TableAnalysis(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    rows: list[dict[str, str | float | None]] = Field(min_length=1, max_length=500)
    column: str = Field(min_length=1, max_length=100)
    group_by: str | None = Field(default=None, min_length=1, max_length=100)
    minimum: float | None = None
    maximum: float | None = None
    @model_validator(mode='after')
    def budgets(self):
        if len(json.dumps(self.rows, allow_nan=False)) > 20000: raise ValueError('Table budget exceeded')
        for row in self.rows:
            if len(row)>20 or any(len(k)>100 for k in row): raise ValueError('Column budget exceeded')
        for value in (self.minimum, self.maximum):
            if value is not None and (not math.isfinite(value) or abs(value)>1e15): raise ValueError('Numeric budget')
        return self

def analyze_table(args: dict):
    data = TableAnalysis.model_validate(args)
    groups: dict[str, list[float]] = {}
    invalid = filtered = 0
    for row in data.rows:
        try:
            raw = row.get(data.column)
            if raw is None or isinstance(raw, bool): raise ValueError()
            value = float(raw)
            if not math.isfinite(value) or abs(value)>1e15: raise ValueError()
        except (ValueError, TypeError, OverflowError):
            invalid += 1; continue
        if (data.minimum is not None and value<data.minimum) or (data.maximum is not None and value>data.maximum):
            filtered += 1; continue
        label = str(row.get(data.group_by, '(missing)')) if data.group_by else 'All rows'
        if label not in groups and len(groups)>=50: raise ValueError('Group budget exceeded; at most 50 groups')
        groups.setdefault(label, []).append(value)
    summaries = []
    for label, values in sorted(groups.items()):
        summaries.append({'group':label, 'count':len(values), 'sum':math.fsum(values), 'mean':statistics.mean(values),
                          'median':statistics.median(values), 'min':min(values), 'max':max(values),
                          'population_stddev':statistics.pstdev(values)})
    # Self-contained SVG with no scripts, remote resources or unescaped labels.
    scale = max([abs(s['sum']) for s in summaries] or [1]) or 1
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="640" height="%d" role="img" aria-label="Group totals">' % (40+len(summaries)*30)]
    for i, item in enumerate(summaries):
        y = 20+i*30
        svg.append(f'<text x="5" y="{y+12}">{escape(item["group"][:30])}</text><rect x="260" y="{y}" width="{abs(item["sum"])/scale*220:.2f}" height="18" fill="#3478cc"/><text x="490" y="{y+12}">{item["sum"]:.6g}</text>')
    return {'groups':summaries, 'invalid_rows':invalid, 'filtered_rows':filtered, 'chart_svg':''.join(svg)+'</svg>',
            'warning':'Deterministic supplied-data statistics; source accuracy is not verified. Bar length shows absolute total; labels retain sign.'}

def source_zip(project: dict) -> bytes:
    validated = SourceProject.model_validate(project)
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(validated.files.items()):
            archive.writestr(name, content.encode('utf-8'))
    return out.getvalue()

def text_export(title: str, body: str, format: Literal['json','csv']):
    if format=='json': return json.dumps({'title':title, 'body':body},ensure_ascii=False).encode(), 'application/json'
    out=io.StringIO(newline=''); writer=csv.writer(out)
    def safe(value): return "'"+value if value.startswith(('=', '+', '-', '@', '\t', '\r')) else value
    writer.writerow(['title','body']);writer.writerow([safe(title),safe(body)])
    return out.getvalue().encode('utf-8-sig'),'text/csv'
