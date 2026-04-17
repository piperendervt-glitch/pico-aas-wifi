"""
Pico 2W 設定テンプレート
使い方:
  1. このファイルを config.py にコピー
  2. WIFI_SSID / WIFI_PASS / SERVER_IP / NODE_ID を書き換える
  3. config.py は git 管理外（.gitignore 済み）

3台運用時の NODE_ID 例:
    Pico #1 → NODE_ID = "pico-1"
    Pico #2 → NODE_ID = "pico-2"
    Pico #3 → NODE_ID = "pico-3"
"""

# ========== WiFi ==========
WIFI_SSID = "YOUR_WIFI_SSID"        # WiFi名
WIFI_PASS = "YOUR_WIFI_PASSWORD"    # WiFiパスワード

# ========== サーバー ==========
SERVER_IP = "192.168.1.100"         # PCのIPアドレス（ipconfig で確認）
SERVER_PORT = 5001

# ========== ノード ==========
NODE_ID = "pico-1"                  # pico-1, pico-2, pico-3 のいずれか

# ========== 動作 ==========
SEND_INTERVAL = 5                   # 送信間隔（秒）
SENSOR_PIN = 15                     # AM2302 DATA → GP15
MAX_RETRIES = 3                     # 送信リトライ回数
