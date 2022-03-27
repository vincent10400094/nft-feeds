import os
import threading
import signal
import sys

from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from scanner import Scanner
from db import Database

load_dotenv()

app = Flask(__name__)
CORS(app)

db = Database(capacity=int(
    os.environ['DB_CAPACITY']), db_path=os.environ['DB_PATH'])
scanner = Scanner(os.environ['ETH_RPC_URL'], db)


def sigint_handler(sig, frame):
    print('Saving database and stop gracefully...')
    db.save()
    sys.exit(0)


def scan_job():
    scanner.scan()
    threading.Timer(5.0, scan_job).start()


signal.signal(signal.SIGINT, sigint_handler)
scan_worker = threading.Timer(0.0, scan_job)
scan_worker.start()


@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({
        'message': 'Hello world'
    })


@app.route('/api/nfts', methods=['GET'])
def get_feeds():
    return jsonify(db.query_all()[::-1])


if __name__ == '__main__':
    app.run(host=os.environ['HOST_IP'], port=os.environ['PORT'])
