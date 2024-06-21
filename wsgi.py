# wsgi.py
from app import create_app, socketio
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler

app = create_app()

if __name__ == "__main__":
    server = pywsgi.WSGIServer(('0.0.0.0', 5000), app, handler_class=WebSocketHandler)
    server.serve_forever()
