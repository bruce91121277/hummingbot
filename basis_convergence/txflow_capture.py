"""Bounded unauthenticated public market capture on Oracle."""
import argparse
import asyncio
import hashlib
import json
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import websockets


def query(url, payload=None):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "x-api-version": "2026-08-16",
    }
    with urlopen(
        Request(url, data=json.dumps(payload).encode() if payload is not None else None, headers=headers),
        timeout=15,
    ) as response:
        return json.load(response)


def now():
    return datetime.now(timezone.utc).isoformat()


async def main(root, seconds):
    if not 1 <= seconds <= 3600:
        raise ValueError("duration must be between 1 and 3600 seconds")
    tx = query("https://rpc.txflow.com/info", {"type": "perpMeta", "includeDelisted": False})
    lighter = query("https://mainnet.zklighter.elliot.ai/api/v1/orderBooks")
    txbtc = [
        x for x in tx["data"]["universe"]
        if x.get("baseCurrency") == "BTC" and x.get("quoteCurrency") == "USDC"
        and not x.get("delisted") and not x.get("haltTrading")
    ]
    core = [
        x for x in lighter["order_books"]
        if x.get("symbol") == "BTC" and x.get("market_type") == "perp"
        and x.get("status") == "active" and x.get("market_deployer") == "lighter"
    ]
    if len(txbtc) != 1 or len(core) != 1:
        raise ValueError("market discovery is ambiguous")
    txbtc, core = txbtc[0], core[0]
    ident, lid = str(txbtc["index"]), str(core["market_id"])
    root.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(root).free
    required_bytes = max(128 * 1024 * 1024, seconds * 32 * 1024)
    if free_bytes < required_bytes + 64 * 1024 * 1024:
        raise OSError(f"insufficient free disk: {free_bytes} bytes available")
    directory = root / ("capture_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:6])
    directory.mkdir()
    discovery = {
        "retrieved_utc": now(),
        "sources": {"txflow": tx, "lighter_core": lighter},
        "markets": {"txflow": {"BTC": txbtc}, "lighter_core": {"BTC": core}},
    }
    (directory / "discovery.json").write_text(json.dumps(discovery, separators=(",", ":")))

    started = now()
    deadline = time.monotonic() + seconds
    event_cap = min(250000, max(20000, seconds * 35))
    counts, errors, segments = {}, {}, {}

    async def stream(venue, url, subscription):
        count, segment = 0, 0
        errors[venue], segments[venue] = [], []
        output = (directory / (venue + ".jsonl")).open("x")
        ping_at = time.monotonic() + 10
        try:
            while time.monotonic() < deadline and count < event_cap:
                segment += 1
                segment_start = now()
                record = {"segment_id": segment, "start_utc": segment_start}
                try:
                    async with websockets.connect(
                        url,
                        additional_headers={"User-Agent": "Mozilla/5.0"},
                        open_timeout=12,
                        close_timeout=2,
                        max_size=8 * 1024 * 1024,
                        ping_interval=20,
                        ping_timeout=10,
                    ) as ws:
                        await ws.send(json.dumps(subscription))
                        while time.monotonic() < deadline and count < event_cap:
                            if venue == "txflow" and time.monotonic() >= ping_at:
                                await ws.send('{"method":"ping"}')
                                ping_at = time.monotonic() + 10
                            try:
                                raw = await asyncio.wait_for(
                                    ws.recv(), min(1, max(0.01, deadline - time.monotonic()))
                                )
                            except asyncio.TimeoutError:
                                continue
                            received, mono = time.time_ns(), time.monotonic_ns()
                            msg = json.loads(raw)
                            if msg.get("type") == "error" or msg.get("channel") == "error":
                                raise RuntimeError("websocket error: " + str(msg)[:160])
                            if venue == "txflow":
                                if msg.get("channel") != "l2Book":
                                    continue
                                body = msg.get("data", {})
                                if body.get("coin") != "BTC-USDC":
                                    errors[venue].append("unexpected market identity")
                                    continue
                                source, sequence, market, unit = body.get("time"), None, ident, "ms_documented"
                            else:
                                if msg.get("channel") != "order_book:" + lid:
                                    continue
                                body = msg.get("order_book", {})
                                source, sequence, market, unit = body.get("last_updated_at", msg.get("last_updated_at")), body.get("nonce"), lid, "us_UNVERIFIED"
                                if msg.get("type") not in ("subscribed/order_book", "update/order_book"):
                                    errors[venue].append("unexpected order-book message type")
                                    continue
                            row = {
                                "venue": venue, "stream": "orderbook", "market_id": market,
                                "segment_id": segment, "received_utc_ns": received,
                                "received_mono_ns": mono, "source_timestamp": source,
                                "source_timestamp_unit": unit, "sequence": sequence, "message": msg,
                            }
                            output.write(json.dumps(row, separators=(",", ":")) + "\n")
                            count += 1
                    record["stop_reason"] = "EVENT_CAP" if count >= event_cap else "CAPTURE_END"
                except Exception as exc:
                    description = type(exc).__name__ + ": " + str(exc)[:200]
                    errors[venue].append(description)
                    record["error"] = description
                    record["stop_reason"] = "DISCONNECT"
                    if time.monotonic() < deadline and count < event_cap:
                        await asyncio.sleep(min(8, 2 ** min(segment - 1, 3)))
                record["end_utc"] = now()
                segments[venue].append(record)
        finally:
            output.close()
            counts[venue] = count

    await asyncio.gather(
        stream("txflow", "wss://rpc.txflow.com/ws", {
            "method": "subscribe", "type": "l2Book",
            "subscription": {"type": "l2Book", "coin": ident},
        }),
        stream("lighter_core", "wss://mainnet.zklighter.elliot.ai/stream?readonly=true", {
            "type": "subscribe", "channel": "order_book/" + lid,
        }),
    )
    files = {}
    for file in directory.iterdir():
        raw = file.read_bytes()
        files[file.name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    manifest = {
        "start_utc": started, "end_utc": now(), "events": counts, "errors": errors,
        "segments": segments, "files": files, "source": "PUBLIC_ONLY",
        "max_seconds": seconds, "event_cap_per_venue": event_cap,
        "disk_preflight": {"free_bytes": free_bytes, "required_bytes": required_bytes},
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"path": str(directory), "events": counts, "errors": errors, "segments": {k: len(v) for k, v in segments.items()}}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=300)
    args = parser.parse_args()
    asyncio.run(main(args.output_root, args.seconds))
