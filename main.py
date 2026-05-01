import sys

try:
    print("Starting test script...", flush=True)
    from flask import Flask
    print("Flask imported OK", flush=True)

    app = Flask(__name__)

    @app.route("/")
    def home():
        return "Test OK - Flask is working!"

    print("About to run app...", flush=True)
    app.run(host="0.0.0.0", port=8080)

except Exception as e:
    print("FATAL ERROR:", str(e), file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
