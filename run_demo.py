import webbrowser
import threading
import time
from app import app

def open_browser():
    time.sleep(1.5)
    print("\n" + "="*60)
    print(">> ClipGenie AI-in-Education Practice Studio Launched!")
    print(">> URL: http://127.0.0.1:5000/practice")
    print(">> Instructor View: http://127.0.0.1:5000/instructor")
    print("="*60 + "\n")
    try:
        webbrowser.open("http://127.0.0.1:5000/practice")
    except Exception as e:
        print(f"Could not automatically open browser: {e}")

if __name__ == '__main__':
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='127.0.0.1', port=5000, debug=False)
