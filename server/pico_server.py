"""
Pico 2W WiFi Data Receiver
物理AAS Phase 1 — PC側サーバー

3台のPico 2WからHTTP POSTで温湿度データを受信し
CSVに記録する。WiFi遅延もR(x)分布データとして保存。

起動: python pico_server.py
"""

from flask import Flask, request, jsonify
import csv
import os
from datetime import datetime

app = Flask(__name__)

# リポジトリルートの data/ に保存
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# CSVファイル: センサーデータ
DATA_FILE = os.path.join(DATA_DIR, "sensor_data.csv")
# CSVファイル: WiFi遅延ログ（R(x)分布データ）
LATENCY_FILE = os.path.join(DATA_DIR, "wifi_latency.csv")

# CSVヘッダー初期化
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "node_id", "temperature", "humidity",
            "uptime_ms", "wifi_rtt_ms"
        ])

if not os.path.exists(LATENCY_FILE):
    with open(LATENCY_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "node_id", "wifi_rtt_ms",
            "uptime_ms", "send_attempt"
        ])

# ノード状態の追跡
nodes = {}


@app.route("/data", methods=["POST"])
def receive_data():
    """Pico 2Wからのセンサーデータ受信"""
    server_time = datetime.now()

    try:
        data = request.get_json()
    except Exception:
        return jsonify({"error": "invalid json"}), 400

    if data is None:
        return jsonify({"error": "invalid json"}), 400

    node_id = data.get("node_id", "unknown")
    temp = data.get("temperature")
    hum = data.get("humidity")
    uptime = data.get("uptime_ms", 0)
    rtt = data.get("wifi_rtt_ms", 0)
    attempt = data.get("send_attempt", 1)

    # センサーデータ記録
    with open(DATA_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            server_time.isoformat(),
            node_id, temp, hum, uptime, rtt
        ])

    # WiFi遅延ログ記録（R(x)分布データ）
    with open(LATENCY_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            server_time.isoformat(),
            node_id, rtt, uptime, attempt
        ])

    # ノード状態更新
    nodes[node_id] = {
        "last_seen": server_time.isoformat(),
        "temperature": temp,
        "humidity": hum,
        "rtt": rtt,
        "uptime_ms": uptime,
    }

    print(
        f"[{server_time.strftime('%H:%M:%S')}] "
        f"Node {node_id}: {temp}°C / {hum}% "
        f"(RTT: {rtt}ms, attempt: {attempt})"
    )

    return jsonify({"status": "ok", "server_time": server_time.isoformat()})


@app.route("/status", methods=["GET"])
def status():
    """全ノードの現在状態を返す"""
    return jsonify({
        "nodes": nodes,
        "node_count": len(nodes),
        "server_time": datetime.now().isoformat(),
    })


@app.route("/", methods=["GET"])
def index():
    """簡易ステータスページ"""
    html = "<h2>Pico 2W Data Receiver</h2>"
    html += f"<p>Active nodes: {len(nodes)}</p>"
    if nodes:
        html += "<table border='1' cellpadding='6'>"
        html += "<tr><th>Node</th><th>Temp</th><th>Hum</th><th>RTT</th><th>Last seen</th></tr>"
        for nid, info in sorted(nodes.items()):
            html += (
                f"<tr><td>{nid}</td>"
                f"<td>{info['temperature']}°C</td>"
                f"<td>{info['humidity']}%</td>"
                f"<td>{info['rtt']}ms</td>"
                f"<td>{info['last_seen']}</td></tr>"
            )
        html += "</table>"
    else:
        html += "<p>Waiting for Pico 2W connections...</p>"
    html += f"<p>Data: {DATA_FILE}</p>"
    html += f"<p>Latency log: {LATENCY_FILE}</p>"
    return html


if __name__ == "__main__":
    print("=" * 50)
    print("Pico 2W Data Receiver")
    print("Physical AAS Phase 1")
    print("=" * 50)
    print(f"Data file:    {DATA_FILE}")
    print(f"Latency file: {LATENCY_FILE}")
    print("Endpoints:")
    print("  POST /data   - receive sensor data")
    print("  GET  /status - node status (JSON)")
    print("  GET  /       - status page (HTML)")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5001, debug=True)
