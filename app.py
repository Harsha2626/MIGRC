import sys

from app import create_app

app = create_app()

if __name__ == '__main__':
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    app.run(debug=True, port=5000, threaded=True, use_reloader=True)
