import os
import sys

from app import create_app

app = create_app()

if __name__ == '__main__':
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, port=5000, threaded=True, use_reloader=debug)
