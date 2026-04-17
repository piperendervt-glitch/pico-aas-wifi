"""
Pico 2W WiFi Sender
物理AAS Phase 1 — Pico側 MicroPython

AM2302で温湿度を読み取り、WiFi経由でPCサーバーにHTTP POSTする。
WiFi RTTもR(x)分布データとして計測・送信。

準備:
  1. config_example.py をコピーして config.py を作成
  2. config.py の WIFI_SSID / WIFI_PASS / SERVER_IP / NODE_ID を設定
  3. Thonnyで main.py と config.py を Pico に書き込む

LED表示:
  接続成功: 3回点滅
  送信成功: 1回短く点滅
  接続失敗: 高速点滅 → 10秒後に再起動
"""

import machine
import dht
import network
import urequests
import ujson
import time

import config

# LED（オンボード）
led = machine.Pin("LED", machine.Pin.OUT)

# AM2302センサー（GP15 内蔵プルアップ）
pin = machine.Pin(config.SENSOR_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
sensor = dht.DHT22(pin)


def blink(n=1, on_ms=100, off_ms=100):
    """LEDを点滅"""
    for _ in range(n):
        led.on()
        time.sleep_ms(on_ms)
        led.off()
        time.sleep_ms(off_ms)


def connect_wifi():
    """WiFi接続"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print(f"Already connected: {wlan.ifconfig()[0]}")
        return wlan

    print(f"Connecting to {config.WIFI_SSID}...")
    wlan.connect(config.WIFI_SSID, config.WIFI_PASS)

    timeout = 20
    while not wlan.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1
        print(f"  waiting... ({20 - timeout}s)")

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"Connected! IP: {ip}")
        blink(3)  # 接続成功: 3回点滅
        return wlan
    else:
        print("WiFi connection failed!")
        blink(10, 50, 50)  # 接続失敗: 高速点滅
        return None


def read_sensor():
    """AM2302からデータ読み取り"""
    try:
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
        return temp, hum
    except Exception as e:
        print(f"Sensor error: {e}")
        return None, None


def send_data(temp, hum):
    """PCサーバーにHTTP POSTでデータ送信"""
    url = f"http://{config.SERVER_IP}:{config.SERVER_PORT}/data"
    uptime = time.ticks_ms()

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            # RTT計測開始
            t_start = time.ticks_ms()

            payload = ujson.dumps({
                "node_id": config.NODE_ID,
                "temperature": temp,
                "humidity": hum,
                "uptime_ms": uptime,
                "wifi_rtt_ms": 0,  # サーバー側では計測後RTTで上書き計算する場合用
                "send_attempt": attempt,
            })

            response = urequests.post(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
            )

            # RTT計測完了
            rtt = time.ticks_diff(time.ticks_ms(), t_start)

            if response.status_code == 200:
                print(f"  Sent OK (RTT: {rtt}ms, attempt: {attempt})")
                # 送信成功: 1回短く点滅
                blink(1, on_ms=50, off_ms=0)
                response.close()
                return True, rtt
            else:
                print(f"  HTTP {response.status_code} (attempt {attempt})")
                response.close()

        except Exception as e:
            print(f"  Send error (attempt {attempt}): {e}")

        time.sleep(1)  # リトライ前に1秒待機

    return False, 0


def main():
    """メインループ"""
    print("=" * 40)
    print(f"Pico 2W Sensor Node: {config.NODE_ID}")
    print(f"Server: {config.SERVER_IP}:{config.SERVER_PORT}")
    print(f"Interval: {config.SEND_INTERVAL}s")
    print("=" * 40)

    # WiFi接続
    wlan = connect_wifi()
    if not wlan:
        print("Rebooting in 10s...")
        time.sleep(10)
        machine.reset()

    # センサー初期化待ち
    time.sleep(2)

    # メインループ
    while True:
        temp, hum = read_sensor()

        if temp is not None:
            print(f"[{config.NODE_ID}] {temp}°C / {hum}%")
            ok, rtt = send_data(temp, hum)

            if not ok:
                print("  All retries failed. Checking WiFi...")
                if not wlan.isconnected():
                    wlan = connect_wifi()
                    if not wlan:
                        print("Rebooting in 10s...")
                        time.sleep(10)
                        machine.reset()
        else:
            print("Sensor read failed, retrying...")

        time.sleep(config.SEND_INTERVAL)


# 起動
main()
