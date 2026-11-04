import csv
import io
from flask import Response


_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


def sanitize_cell(value):
    """Neutralise spreadsheet formula injection: text cells that start with a formula trigger
    character get a leading single quote so Excel/Sheets treat them as text."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def csv_response(filename, headers, rows):
    """rows: iterable of iterables matching headers. Returns a downloadable CSV Flask Response."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([sanitize_cell(h) for h in headers])
    for row in rows:
        writer.writerow([sanitize_cell(v) for v in row])
    return Response(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )
