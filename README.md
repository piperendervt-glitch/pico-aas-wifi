# pico-aas-wifi

Raspberry Pi Pico 2W × 3台から PC へ WiFi 経由で温湿度データを送信する
物理 AAS (Asset Administration Shell) Phase 1 実験用リポジトリ。

センサーは **AM2302 (DHT22)**、通信は **HTTP POST (JSON)**、
保存は **CSV**。WiFi RTT も R(x) 分布データとして記録する（PHNN 研究用）。

## 構成

```
pico-aas-wifi/
├── README.md
├── server/
│   └── pico_server.py       # PC側 Flask 受信サーバー
├── pico/
│   ├── main.py              # Pico側 MicroPython 送信コード
│   └── config_example.py    # 設定テンプレート
└── data/                    # CSV ログ保存先（.gitignore）
```

## PC 側セットアップ

### 1. Flask インストール

```bash
pip install flask
```

### 2. PC の IP アドレスを確認

Windows:

```bash
ipconfig
```

「IPv4 アドレス」（例: `192.168.1.100`）をメモしておく。
この値を各 Pico の `config.py` の `SERVER_IP` に設定する。

### 3. サーバー起動

```bash
cd server
python pico_server.py
```

エンドポイント:

- `POST /data`   センサーデータ受信（Pico からの送信先）
- `GET  /status` 全ノード状態（JSON）
- `GET  /`       HTML ステータスページ（ブラウザで `http://<PC_IP>:5001/`）

CSV は `data/` に保存:

- `data/sensor_data.csv` — `timestamp, node_id, temperature, humidity, uptime_ms, wifi_rtt_ms`
- `data/wifi_latency.csv` — `timestamp, node_id, wifi_rtt_ms, uptime_ms, send_attempt`

### 4. Windows ファイアウォール

初回起動時にポート 5001 の受信を許可するダイアログが出る場合は許可する。
LAN 内の Pico から PC にアクセスできない場合はファイアウォール設定を確認。

## Pico 側セットアップ

### 配線（AM2302 / DHT22）

| AM2302 ピン | 接続先 Pico ピン | 備考                            |
|:-----------:|:----------------:|:--------------------------------|
| VCC         | Pin 36 (3V3 OUT) | 電源 +3.3V                      |
| DATA        | GP15 (Pin 20)    | 内蔵プルアップを使用            |
| NC          | —                | 未接続                          |
| GND         | Pin 38 (GND)     | グラウンド                      |

外付けプルアップ抵抗は不要（`main.py` で `Pin.PULL_UP` を指定済み）。

### MicroPython のインストール

Thonny で Pico 2W を選択し、MicroPython ファームウェアをインストール。

### コード転送（3台それぞれで実施）

1. `pico/config_example.py` を PC 側でコピーして `pico/config.py` を作成
2. `config.py` の以下を書き換え:

   ```python
   WIFI_SSID = "あなたのWiFi名"
   WIFI_PASS = "あなたのWiFiパスワード"
   SERVER_IP = "192.168.1.100"   # PC の IPv4
   NODE_ID   = "pico-1"          # 各 Pico で変える
   ```

3. 3台の NODE_ID をそれぞれ次のように変えて転送する:

   | 機体 | `NODE_ID`  |
   |:----:|:----------:|
   | #1   | `pico-1`   |
   | #2   | `pico-2`   |
   | #3   | `pico-3`   |

4. Thonny から Pico に接続 → `pico/main.py` と `pico/config.py` を
   Pico のルート（`/`）に `main.py` と `config.py` として保存する。

   （`config.py` は必ず機体ごとに `NODE_ID` を変えて保存）

5. Pico を再起動すると `main.py` が自動実行される。

### LED で見る状態

| LED の動作       | 意味                       |
|:-----------------|:---------------------------|
| 3回点滅          | WiFi 接続成功              |
| 1回短く点滅      | データ送信成功             |
| 高速点滅         | WiFi 接続失敗（10秒後再起動）|

## 動作確認

1. PC で `python server/pico_server.py` を起動
2. 3台の Pico に電源を入れる
3. ブラウザで `http://<PC_IP>:5001/` を開く
4. 3ノード分の温湿度・RTT が表示されれば成功
5. `data/sensor_data.csv` と `data/wifi_latency.csv` にログが追記される

## セキュリティ注意

- `config.py` は WiFi パスワードを含むため `.gitignore` で除外済み。
  **絶対に commit しない**こと。
- `data/` も実測データを含むため除外済み。
