from app import create_app
import threading
import time
import requests

app = create_app("development")
app.config["WTF_CSRF_ENABLED"] = True
app.config["TESTING"] = False # Ensure testing mode is off

def run_app():
    app.run(port=5001, debug=False, use_reloader=False)

threading.Thread(target=run_app, daemon=True).start()
time.sleep(2)

session = requests.Session()
# We need to bypass login or just hit the API if login isn't required?
# Oh, @login_required is there. 
# We can bypass login_required for this test by monkeypatching it,
# but the easiest way is to let login_required redirect us. Wait.
