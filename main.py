import os
import sys

try:
    print(">>> Starting test script...", flush=True, file=sys.stderr)
    from flask import Flask
    print(">>> Flask imported OK", flush=True, file=sys.stderr)

    app = Flask(__name__)

    @app.route("/")
    def home():
        return "Test OK - Flask is working!"

    port = int(os.environ.get("PORT", 8080))
    print(f">>> Running on port {port}...", flush=True, file=sys.stderr)
    app.run(host="0.0.0.0", port=port)

except Exception as e:
    print(f">>> FATAL ERROR: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
