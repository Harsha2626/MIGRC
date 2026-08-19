import csv
import io
from flask import Response


def csv_response(filename, headers, rows):
    """rows: iterable of iterables matching headers. Returns a downloadable CSV Flask Response."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )
