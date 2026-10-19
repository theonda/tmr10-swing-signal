"""Optional GitHub Actions runner: scans daily and sends Telegram notifications for newly confirmed signals."""
import os
import json
import pathlib
import requests
from scanner import WATCHLIST, download_daily, scan

STATE = pathlib.Path("signal_state.json")

def main():
    old = json.loads(STATE.read_text()) if STATE.exists() else {}
    state = dict(old)
    messages = []
    for ticker, name in WATCHLIST.items():
        try:
            result = scan(ticker, name, download_daily(ticker))
        except Exception as e:
            print(f"SKIP {ticker}: {e}")
            continue
        key = f"{result.date}|{result.signal}"
        if result.signal != "確認待ち" and old.get(ticker) != key:
            messages.append(f"📈 {name} ({ticker})\n{result.date} / {result.signal}\n終値 {result.close:,.2f} / 基準 {result.trigger:,.2f}\n出来高 {result.volume_ratio:.2f}倍 / 参考損切り {result.stop:,.2f}\n{result.description}\nTMR10・決算・業種強度は要確認\n{result.source}")
            state[ticker] = key
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if messages and (not token or not chat_id):
        print("Signals detected, but Telegram credentials are unset; no messages sent")
        print("\n---\n".join(messages))
        return
    for message in messages:
        response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id":chat_id,"text":message}, timeout=20)
        response.raise_for_status()
    if state != old:
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    print(f"Checked {len(WATCHLIST)} names; sent {len(messages)} alert(s)")

if __name__ == "__main__":
    main()
