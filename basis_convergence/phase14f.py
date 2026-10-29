"""Phase 14F: event-driven, public-capture basis diagnostics (all PnL is hypothetical)."""
import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path

from basis_convergence.capture import read_extended_core
from basis_convergence.engine import NS, diagnose, latest, replay, walk

FEE_CASES = {"zero": (D(0), D(0)), "txflow_4_5bps": (D("4.5"), D(0))}
MODES = ("event", 100, 250, 1000)
STRATEGIES = {
    "convergence_25": ("percent", D(".25")),
    "convergence_50": ("percent", D(".50")),
    "basis_le_2bps": ("basis", D(".25")),
    "net_profit_positive": ("net", D(".25")),
    "convergence_and_net_positive": ("combined", D(".25")),
    "stop_loss_10bps": ("stop", D(".25")),
    "timeout": ("timeout", D(".25")),
}

def capture_paths(root):
    root = Path(root)
    if (root / "manifest.json").is_file():
        return [root]
    return sorted(p.parent for p in root.rglob("manifest.json") if p.parent.name.startswith("capture_"))

def end_time(manifest, left, right):
    seen = max(left[-1].mono, right[-1].mono)
    if manifest.get("end_utc"):
        anchor = left[-1]
        utc_end = int(datetime.fromisoformat(manifest["end_utc"]).timestamp() * NS)
        return max(seen, anchor.mono + utc_end - anchor.utc)
    return seen

def event_pairs(left, right, freshness_ms=500):
    """Yield each newly received quote pair, including invalid books, without look-ahead."""
    times = sorted({q.mono for q in left + right})
    seen = None
    for t in times:
        a, b = latest(left, t), latest(right, t)
        if not a or not b:
            continue
        key = (a.mono, b.mono)
        if key == seen:
            continue
        seen = key
        yield t, a, b, diagnose(a, b, t, freshness_ms)

def edge_metrics(a, b, notional=D(100)):
    valid_a = bool(a.bids and a.asks)
    valid_b = bool(b.bids and b.asks)
    am = (a.bids[0][0] + a.asks[0][0]) / 2 if valid_a else None
    bm = (b.bids[0][0] + b.asks[0][0]) / 2 if valid_b else None
    if not valid_a or not valid_b:
        return {
            "txflow_mid": am, "lighter_mid": bm, "mid_basis_bps_txflow_over_lighter": None,
            "txflow_spread_bps": (a.asks[0][0] - a.bids[0][0]) / am * 10000 if valid_a else None,
            "lighter_spread_bps": (b.asks[0][0] - b.bids[0][0]) / bm * 10000 if valid_b else None,
            "edge_short_txflow_long_lighter_bps": None, "edge_long_txflow_short_lighter_bps": None,
            "direction": None, "best_bbo_edge_bps": None, "l2_vwap_edge_bps": None,
            "notional_assumed": str(notional), "quantity_assumed": None,
        }
    mid = (am + bm) / 2
    edge_tx_short = (a.bids[0][0] - b.asks[0][0]) / b.asks[0][0] * 10000
    edge_tx_long = (b.bids[0][0] - a.asks[0][0]) / a.asks[0][0] * 10000
    direction = "SHORT_TXFLOW_LONG_LIGHTER" if edge_tx_short >= edge_tx_long else "LONG_TXFLOW_SHORT_LIGHTER"
    raw_edge = max(edge_tx_short, edge_tx_long)
    qty = notional / mid
    if direction == "SHORT_TXFLOW_LONG_LIGHTER":
        qa, pa = walk(a, "sell", qty)
        qb, pb = walk(b, "buy", qty)
        l2edge = (pa - pb) / pb * 10000 if pa is not None and pb is not None and qa >= qty and qb >= qty else None
    else:
        qa, pa = walk(a, "buy", qty)
        qb, pb = walk(b, "sell", qty)
        l2edge = (pb - pa) / pa * 10000 if pa is not None and pb is not None and qa >= qty and qb >= qty else None
    return {
        "txflow_mid": am, "lighter_mid": bm, "mid_basis_bps_txflow_over_lighter": (am - bm) / mid * 10000,
        "txflow_spread_bps": (a.asks[0][0] - a.bids[0][0]) / am * 10000,
        "lighter_spread_bps": (b.asks[0][0] - b.bids[0][0]) / bm * 10000,
        "edge_short_txflow_long_lighter_bps": edge_tx_short,
        "edge_long_txflow_short_lighter_bps": edge_tx_long,
        "direction": direction, "best_bbo_edge_bps": raw_edge, "l2_vwap_edge_bps": l2edge,
        "notional_assumed": str(notional), "quantity_assumed": str(qty),
    }

def round_trip_cost(a, b, side_left, qty, fee_left, fee_right):
    side_right = "buy" if side_left == "sell" else "sell"
    cash = D(0)
    fees = D(0)
    for q, side, fee in ((a, side_left, fee_left), (b, side_right, fee_right),
                         (a, "buy" if side_left == "sell" else "sell", fee_left),
                         (b, "sell" if side_right == "buy" else "buy", fee_right)):
        filled, px = walk(q, side, qty)
        if px is None or filled < qty:
            return None
        cash += (D(1) if side == "sell" else D(-1)) * filled * px
        fees += filled * px * fee / D(10000)
    notional = qty * ((a.bids[0][0] + a.asks[0][0] + b.bids[0][0] + b.asks[0][0]) / 4)
    return {"fee_only_bps": str(D(2) * (fee_left + fee_right)),
            "same_basis_four_leg_cost_quote": str(max(D(0), fees - cash)),
            "same_basis_break_even_bps": str(max(D(0), fees - cash) / notional * 10000),
            "fees_quote": str(fees), "cash_flow_quote": str(cash)}

def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list, tuple)) else v for k, v in row.items()})

def pct(values, p):
    if not values:
        return None
    if not 1 <= p <= 100:
        raise ValueError("percentile must be between 1 and 100")
    ordered = sorted(values)
    return ordered[max(0, (p * len(ordered) + 99) // 100 - 1)]

def quote_classification(reasons, values):
    codes = {reason for _, reason in reasons}
    if codes & {"SOURCE_TIMESTAMP_STALE", "RECEIVE_TIMESTAMP_STALE", "SOURCE_TIMESTAMP_IN_FUTURE"}:
        return "STALE_QUOTE_SUSPECT", ["STALE_QUOTE_SUSPECT"]
    if codes & {"SEQUENCE_GAP", "CONNECTION_SEGMENT_CHANGED", "ORDERBOOK_INVALID"}:
        return "BOOK_OR_SEQUENCE_INVALID", ["BOOK_OR_SEQUENCE_INVALID"]
    if reasons:
        return "CLOCK_UNCERTAIN", ["CLOCK_UNCERTAIN"]
    if values["l2_vwap_edge_bps"] is None:
        return "INSUFFICIENT_DEPTH", ["INSUFFICIENT_DEPTH"]
    if values["best_bbo_edge_bps"] >= 10:
        return "DIRECTIONAL_BASIS_CANDIDATE", [
            "DIRECTIONAL_BASIS_CANDIDATE", "CONTRACT_SPECIFICATION_UNVERIFIED", "CLOCK_SYNC_UNVERIFIED"
        ]
    return "BELOW_THRESHOLD_OR_UNEXPLAINED", ["BELOW_THRESHOLD_OR_UNEXPLAINED"]

def summarize_execution(rows):
    groups = {}
    counts = ("signals", "first_leg_fills", "executed_entry_pairs", "closed", "convergence_exits",
              "net_profit_exits", "stop_losses", "timeouts", "censored", "hedge_failures")
    for row in rows:
        key = (row["sample_group"], row["decision_mode"], row["strategy"],
               row["max_hold_seconds"], row["fee_scenario"])
        group = groups.setdefault(key, {
            **{name: 0 for name in counts}, "sample_group": key[0], "decision_mode": key[1],
            "strategy": key[2], "max_hold_seconds": key[3], "fee_scenario": key[4],
            "_net": D(0), "_open": [],
        })
        for name in counts:
            group[name] += int(row.get(name, 0))
        group["_net"] += D(row["closed_net_pnl_quote"])
        group["_open"].extend(row.get("last_open_estimates", []))
    result = []
    for group in groups.values():
        net, closed = group.pop("_net"), group["closed"]
        group["closed_net_pnl_quote"] = str(net)
        group["mean_closed_net_pnl_quote"] = str(net / closed) if closed else None
        group["last_open_estimates_quote"] = group.pop("_open")
        result.append(group)
    return sorted(result, key=lambda row: (row["sample_group"], str(row["decision_mode"]),
                                           row["strategy"], row["max_hold_seconds"], row["fee_scenario"]))


def cap_duration(left, right, end):
    return str(D(end - max(left[0].mono, right[0].mono)) / NS)

def analyze(roots, out):
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("output directory must be empty")
    out.mkdir(parents=True, exist_ok=True)
    paths = sorted({p for root in roots for p in capture_paths(root)})
    quote_rows, trades_all, survival_rows, execution, breakeven_rows, residual, capture_summaries = [], [], [], [], [], [], []
    basis_groups = defaultdict(list)
    mid_basis_groups = defaultdict(list)
    entry_quality = Counter()
    all_loaded = []
    for path in paths:
        try:
            manifest, books, quality = read_extended_core(path, "txflow", sample_interval_ms=None)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            capture_summaries.append({"capture": path.name, "integrity": "EXCLUDED", "reason": str(exc)})
            continue
        discovery = json.loads((path / "discovery.json").read_text()) if (path / "discovery.json").is_file() else {}
        market_metadata = {
            "txflow": discovery.get("markets", {}).get("txflow", {}).get("BTC", {}),
            "lighter_core": discovery.get("markets", {}).get("lighter_core", {}).get("BTC", {}),
        }
        left = books.get(("txflow", "BTC"), [])
        right = books.get(("lighter_core", "BTC"), [])
        if not left or not right:
            capture_summaries.append({"capture": path.name, "integrity": "VERIFIED_HASHES_NO_BOTH_BOOKS", "quality": quality})
            continue
        end = end_time(manifest, left, right)
        tag = "holdout" if "holdout" in str(path).lower() else ("exploration" if "exploration" in str(path).lower() else "historical")
        sample, mid_sample, classes = [], [], Counter()
        for t, a, b, reasons in event_pairs(left, right, 500):
            values = edge_metrics(a, b)
            valid = not reasons
            for venue, reason in reasons:
                entry_quality[venue + ":" + reason] += 1
            classification, flags = quote_classification(reasons, values)
            if valid and values["best_bbo_edge_bps"] is not None and values["best_bbo_edge_bps"] >= 10:
                flags.extend(("LIGHTER_SOURCE_CLOCK_UNVERIFIED", "CROSS_VENUE_CONTRACT_UNVERIFIED"))
            classes[classification] += 1
            if valid and values["best_bbo_edge_bps"] is not None:
                sample.append(values["best_bbo_edge_bps"])
                mid_sample.append(values["mid_basis_bps_txflow_over_lighter"])
                basis_groups[(path.name, tag)].append(values["best_bbo_edge_bps"])
                mid_basis_groups[(path.name, tag)].append(values["mid_basis_bps_txflow_over_lighter"])
            now_utc = a.utc + (t - a.mono)
            quote_rows.append({
                "capture": path.name, "sample_group": tag, "receive_monotonic_ns": t,
                "txflow_bid": str(a.bids[0][0]) if a.bids else None, "txflow_ask": str(a.asks[0][0]) if a.asks else None, "txflow_mid": str(values["txflow_mid"]) if values["txflow_mid"] is not None else None,
                "lighter_bid": str(b.bids[0][0]) if b.bids else None, "lighter_ask": str(b.asks[0][0]) if b.asks else None, "lighter_mid": str(values["lighter_mid"]) if values["lighter_mid"] is not None else None,
                "txflow_spread_bps": str(values["txflow_spread_bps"]) if values["txflow_spread_bps"] is not None else None, "lighter_spread_bps": str(values["lighter_spread_bps"]) if values["lighter_spread_bps"] is not None else None,
                "mid_basis_bps": str(values["mid_basis_bps_txflow_over_lighter"]) if values["mid_basis_bps_txflow_over_lighter"] is not None else None,
                "bbo_edge_bps": str(values["best_bbo_edge_bps"]) if values["best_bbo_edge_bps"] is not None else None,
                "bbo_edge_tx_short_lighter_long_bps": str(values["edge_short_txflow_long_lighter_bps"]) if values["edge_short_txflow_long_lighter_bps"] is not None else None,
                "bbo_edge_tx_long_lighter_short_bps": str(values["edge_long_txflow_short_lighter_bps"]) if values["edge_long_txflow_short_lighter_bps"] is not None else None,
                "l2_vwap_edge_bps": None if values["l2_vwap_edge_bps"] is None else str(values["l2_vwap_edge_bps"]),
                "direction": values["direction"],
                "txflow_source_age_ms": str(D(now_utc - a.source * 1000) / 1000000) if a.source > 0 else None,
                "lighter_source_age_ms": str(D(now_utc - b.source * 1000) / 1000000) if b.source > 0 else None,
                "source_skew_ms": str(D(a.source - b.source) / 1000) if a.source > 0 and b.source > 0 else None,
                "oracle_receive_skew_ms": str(D(a.utc - b.utc) / 1000000),
                "txflow_receive_age_ms": str(D(t - a.mono) / 1000000), "lighter_receive_age_ms": str(D(t - b.mono) / 1000000),
                "txflow_book_age_ms": str(D(t - a.mono) / 1000000), "lighter_book_age_ms": str(D(t - b.mono) / 1000000),
                "monotonic_receive_skew_ms": str(D(a.mono - b.mono) / 1000000),
                "txflow_source_timestamp_raw": a.source_raw, "txflow_source_timestamp_normalized_us": a.source, "lighter_source_timestamp_raw": b.source_raw if b.source_raw is not None else b.source,
                "txflow_receive_utc_ns": a.utc, "lighter_receive_utc_ns": b.utc,
                "txflow_receive_monotonic_ns": a.mono, "lighter_receive_monotonic_ns": b.mono,
                "txflow_segment": a.segment, "lighter_segment": b.segment, "lighter_nonce": b.sequence,
                "economic_units": "UNVERIFIED_CROSS_VENUE", "source_clock": "LIGHTER_MICROSECONDS_ASSUMED_UNVERIFIED",
                "txflow_market_id": market_metadata["txflow"].get("index"), "lighter_market_id": market_metadata["lighter_core"].get("market_id"),
                "quality_flags": flags, "reasons": reasons, "valid_synchronized_500ms": valid,
                "basis_classification": ("DIRECTIONAL_BASIS_CANDIDATE" if values["l2_vwap_edge_bps"] is not None
                                         else "DIRECTIONAL_BASIS_CANDIDATE_DEPTH_INSUFFICIENT")
                                        if valid and values["best_bbo_edge_bps"] is not None and values["best_bbo_edge_bps"] >= 10
                                        else "BELOW_ENTRY_THRESHOLD_OR_INVALID",
                "classification": classification,
            })
        intervals = {v: [D(qs[i].mono - qs[i-1].mono) / NS for i in range(1, len(qs))
                          if qs[i].mono > qs[i-1].mono and qs[i].bids and qs[i].asks and qs[i-1].bids and qs[i-1].asks]
                     for v, qs in (("txflow", left), ("lighter_core", right))}
        duration_ns = max(0, end - min(left[0].mono, right[0].mono))
        duration_seconds = D(duration_ns) / NS
        cap = {"capture": path.name, "sample_group": tag, "integrity": "VERIFIED_SHA256", "manifest_events": manifest.get("events"),
               "reader_quality": quality, "txflow_quotes": len(left), "lighter_quotes": len(right),
               "manifest_errors": manifest.get("errors", {}),
               "connection_segment_counts": {venue: len(segments) for venue, segments in manifest.get("segments", {}).items()},
               "connection_segments": manifest.get("segments", {}),
               "duration_seconds": str(duration_seconds),
               "txflow_update_rate_hz": str(D(len(left)) / duration_seconds) if duration_seconds else None,
               "lighter_update_rate_hz": str(D(len(right)) / duration_seconds) if duration_seconds else None,
               "txflow_update_interval_median_ms": str(pct(intervals["txflow"], 50) * 1000) if intervals["txflow"] else None,
               "txflow_update_interval_p90_ms": str(pct(intervals["txflow"], 90) * 1000) if intervals["txflow"] else None,
               "lighter_update_interval_median_ms": str(pct(intervals["lighter_core"], 50) * 1000) if intervals["lighter_core"] else None,
               "lighter_update_interval_p90_ms": str(pct(intervals["lighter_core"], 90) * 1000) if intervals["lighter_core"] else None,
               "valid_event_pairs": len(sample), "valid_bbo_edge_ge_10bps": sum(x >= 10 for x in sample),
               "mid_basis_median_bps": str(pct(mid_sample, 50)) if mid_sample else None,
               "mid_basis_p90_bps": str(pct(mid_sample, 90)) if mid_sample else None,
               "market_metadata": market_metadata, "classifications": dict(classes)}
        capture_summaries.append(cap)
        all_loaded.append((path, tag, manifest, left, right, end, quality))
    basis_rows = []
    for (name, tag), vals in basis_groups.items():
        mids = mid_basis_groups[(name, tag)]
        basis_rows.append({"capture": name, "sample_group": tag, "samples": len(vals), "positive": sum(x > 0 for x in vals),
                           "edge_ge_10bps": sum(x >= 10 for x in vals), "median_mid_basis_bps": str(pct(mids, 50)),
                           "p90_mid_basis_bps": str(pct(mids, 90)), "median_edge_bps": str(pct(vals, 50)),
                           "p90_edge_bps": str(pct(vals, 90)), "p99_edge_bps": str(pct(vals, 99)),
                           "maximum_edge_bps": str(max(vals)), "holdout_is_independent": tag == "holdout"})
    for path, tag, manifest, left, right, end, quality in all_loaded:
        for mode in MODES:
            for name, (exit_mode, fraction) in STRATEGIES.items():
                for hold in (120, 300, 600):
                    for fee_name, (fl, fr) in FEE_CASES.items():
                        sig, rows, _ = replay(path.name, "BTC-USDC x BTC-Core", left, right, 500, 10, 100,
                                              fraction, hold, fee_left=fl, fee_right=fr, exit_mode=exit_mode,
                                              capture_end_ns=end, decision_ms=mode)
                        closed = [r for r in rows if not r["right_censored"]]
                        execution.append({"capture": path.name, "sample_group": tag, "decision_mode": mode, "strategy": name,
                                          "max_hold_seconds": hold, "fee_scenario": fee_name, "signals": len(sig),
                                          "first_leg_fills": len(rows), "executed_entry_pairs": sum(r["hedge_complete"] for r in rows),
                                          "closed": len(closed), "convergence_exits": sum(r["exit_reason"] == "BASIS_CONVERGED" for r in closed),
                                          "net_profit_exits": sum(r["exit_reason"] == "NET_PROFIT_TARGET" for r in closed),
                                          "stop_losses": sum(r["exit_reason"] == "STOP_LOSS" for r in closed),
                                          "timeouts": sum(r["exit_reason"] == "MAX_HOLD_TIMEOUT" for r in closed),
                                          "censored": sum(r["right_censored"] for r in rows),
                                          "hedge_failures": sum(r["exit_reason"] == "HEDGE_FAILURE" for r in rows),
                                          "closed_net_pnl_quote": str(sum((D(r["net"]) for r in closed), D(0))),
                                          "mean_closed_net_pnl_quote": str(sum((D(r["net"]) for r in closed), D(0)) / len(closed)) if closed else None,
                                          "last_open_estimates": [r["last_liquidation_estimate"] for r in rows if r["right_censored"]],
                                          "right_censored_convergence": sum(r["right_censored"] for r in rows),
                                          "continuous_capture_seconds": cap_duration(left, right, end),
                                          "classification": "HYPOTHETICAL"})
                        for r in rows:
                            entry_a, entry_b = latest(left, r["entry_ns"]), latest(right, r["entry_ns"])
                            if entry_a and entry_b and entry_a.bids and entry_a.asks and entry_b.bids and entry_b.asks:
                                entry_mid_a = (entry_a.bids[0][0] + entry_a.asks[0][0]) / 2
                                entry_mid_b = (entry_b.bids[0][0] + entry_b.asks[0][0]) / 2
                                entry_mid = (entry_mid_a + entry_mid_b) / 2
                                direction_sign = D(1) if r["side_left"] == "sell" else D(-1)
                                initial_basis = D(r["entry_basis_quote_per_btc"]) if r.get("entry_basis_quote_per_btc") is not None else (entry_mid_a - entry_mid_b) * direction_sign
                                initial_basis_bps = D(r["entry_basis_bps"]) if r.get("entry_basis_bps") is not None else (initial_basis / entry_mid * 10000 if entry_mid else None)
                                max_basis = D(r["maximum_observed_basis"]) if r["maximum_observed_basis"] is not None else initial_basis
                                min_basis = D(r["minimum_observed_basis"]) if r["minimum_observed_basis"] is not None else initial_basis
                                r.update({
                                    "entry_basis_quote_per_btc": str(initial_basis),
                                    "entry_basis_bps": str(initial_basis_bps) if initial_basis_bps is not None else None,
                                    "maximum_basis_widening_bps": r.get("maximum_basis_widening_bps") or (str(max(D(0), max_basis - initial_basis) / entry_mid * 10000) if entry_mid else None),
                                    "minimum_observed_basis_quote_per_btc": str(min_basis),
                                    "minimum_observed_basis_bps": r.get("minimum_observed_basis_bps"),
                                    "maximum_observed_basis_bps": r.get("maximum_observed_basis_bps"),
                                    "valid_exit_depth_observed": r["last_liquidation_estimate"] is not None,
                                    "data_gap_count": len(r["gaps"]),
                                    "data_gap_duration_seconds": str(sum((D(g["duration_seconds"]) for g in r["gaps"]), D(0))),
                                    "entry_receive_utc_ns": entry_a.utc + (r["entry_ns"] - entry_a.mono),
                                    "first_25_timestamp_ns": str(int(D(r["hedge_ns"]) + D(r["first_25_seconds"]) * NS)) if r["first_25_seconds"] is not None else None,
                                    "first_50_timestamp_ns": str(int(D(r["hedge_ns"]) + D(r["first_50_seconds"]) * NS)) if r["first_50_seconds"] is not None else None,
                                    "first_net_positive_timestamp_ns": str(int(D(r["hedge_ns"]) + D(r["first_positive_seconds"]) * NS)) if r["first_positive_seconds"] is not None else None,
                                })
                            trade_row = {"capture": path.name, "sample_group": tag, "decision_mode": mode, "strategy": name,
                                         "max_hold_seconds": hold, "fee_scenario": fee_name, **r}
                            for field in ("exit_opportunities", "gaps", "single_leg_risk_observations"):
                                trade_row.pop(field, None)
                            trades_all.append(trade_row)
                            if mode == "event" and name == "timeout" and hold == 600:
                                if not r["survival_eligible"]:
                                    survival_rows.append({"capture": path.name, "sample_group": tag, "trade_id": r["trade_id"],
                                                          "threshold": "paired_position", "status": "NOT_AT_RISK_HEDGE_FAILURE",
                                                          "duration_seconds": None, "event_time_ns": None, "fee_scenario": fee_name})
                                else:
                                    observed_to = min(D(r["observation_duration_seconds"]), D(hold))
                                    for threshold, field in (("25%_convergence", "first_25_seconds"),
                                                             ("50%_convergence", "first_50_seconds"),
                                                             ("four_leg_net_positive", "first_positive_seconds")):
                                        event_seconds = r[field]
                                        survival_rows.append({"capture": path.name, "sample_group": tag, "trade_id": r["trade_id"],
                                                              "threshold": threshold,
                                                              "status": "EVENT" if event_seconds is not None else "RIGHT_CENSORED",
                                                              "duration_seconds": event_seconds if event_seconds is not None else str(observed_to),
                                                              "event_time_ns": (str(int(D(r["hedge_ns"]) + D(event_seconds) * NS)) if event_seconds is not None else None),
                                                              "observation_end_ns": r["capture_end_ns"], "fee_scenario": fee_name,
                                                              "max_hold_seconds": hold, "decision_mode": mode})
                            if r["right_censored"]:
                                residual.append({"capture": path.name, "sample_group": tag, "decision_mode": mode, "strategy": name,
                                                 "max_hold_seconds": hold, "fee_scenario": fee_name,
                                                 "trade_id": r["trade_id"], "exit_reason": r["exit_reason"],
                                                 "inventory": r["inventory"], "entry_fees_paid": r["entry_fees"],
                                                 "unhedged_notional_assumed": r["unhedged_notional_assumed"],
                                                 "last_valid_liquidation_estimate": r["last_liquidation_estimate"],
                                                 "valuation_ns": r["valuation_ns"], "valuation_stale": r["valuation_stale_at_capture_end"],
                                                 "unknown_future_exit_cost": True})
    for path, tag, manifest, left, right, end, quality in all_loaded:
        sig, rows, _ = replay(path.name, "BTC-USDC x BTC-Core", left, right, 500, 10, 100,
                              D(".25"), 600, fee_left=D("4.5"), fee_right=D(0), exit_mode="timeout",
                              capture_end_ns=end, decision_ms="event")
        for r in rows:
            a, b = latest(left, r["entry_ns"]), latest(right, r["entry_ns"])
            if not a or not b or not a.bids or not b.bids:
                continue
            side = "sell" if any(f["id"].endswith(":a") and f["side"] == "sell" for f in r["fills"]) else "buy"
            qty = D(r["fills"][0]["qty"])
            cost = round_trip_cost(a, b, side, qty, D("4.5"), D(0))
            if cost:
                breakeven_rows.append({"capture": path.name, "sample_group": tag, "trade_id": r["trade_id"],
                                       "entry_edge_bps": r["entry_spread_bps"], **cost,
                                       "economic_units": "ASSUMED_BTC_1_TO_1", "fee_assumption": "TxFlow 4.5bps, Lighter 0bps",
                                       "same_snapshot_replenishment_assumed": True,
                                       "interpretation": "optimistic hypothetical four-leg L2 cost; future displayed liquidity is not guaranteed"})
        for delay in (0, 100, 250, 500):
            _, rr, _ = replay(path.name, "BTC-USDC x BTC-Core", left, right, 500, 10, delay,
                              D(".25"), 600, fee_left=D("4.5"), fee_right=D(0), exit_mode="timeout",
                              capture_end_ns=end, decision_ms="event")
            residual.append({"capture": path.name, "sample_group": tag, "mode": "hedge_delay_sensitivity",
                             "hedge_delay_ms": delay, "fee_scenario": "txflow_4_5bps",
                             "entries": len(rr), "hedge_failures": sum(r["exit_reason"] == "HEDGE_FAILURE" for r in rr),
                             "unhedged_notional_assumed": [r["unhedged_notional_assumed"] for r in rr if r["exit_reason"] == "HEDGE_FAILURE"],
                             "counterfactual_emergency_close": [r["emergency_close_scenario"] for r in rr if r["emergency_close_scenario"]],
                             "classification": "HYPOTHETICAL_COUNTERFACTUAL"})
    write_csv(out / "quote_quality.csv", quote_rows)
    write_csv(out / "basis_distribution.csv", basis_rows)
    write_csv(out / "convergence_survival.csv", survival_rows)
    write_csv(out / "breakeven_requirements.csv", breakeven_rows)
    write_csv(out / "execution_comparison.csv", execution)
    write_csv(out / "convergence_trades.csv.gz", trades_all)
    write_csv(out / "residual_exposure.csv", residual)
    summary = {"route": "txflow BTC-USDC x Lighter Core BTC", "classification": "HYPOTHETICAL",
               "captures": capture_summaries, "excluded": [c for c in capture_summaries if c.get("integrity") == "EXCLUDED"],
               "quote_event_pairs": len(quote_rows), "convergence_survival_observations": len(survival_rows), "valid_synchronized_500ms": sum(int(c.get("valid_event_pairs", 0)) for c in capture_summaries),
               "valid_bbo_edge_ge_10bps": sum(int(c.get("valid_bbo_edge_ge_10bps", 0)) for c in capture_summaries),
               "source_clock": "TxFlow time is documented milliseconds; Lighter last_updated_at is assumed microseconds and is unverified. Venue clock synchronization is unknown.",
               "contracts": {"txflow_multiplier": "1 underlying unit per official contract specification", "lighter_multiplier": "metadata says 1, but official semantic, settlement, and cross-venue conversion remain UNVERIFIED", "hedge_ratio": "1:1 BTC assumed only for hypothetical replay", "units": "USDC quote on TxFlow; Lighter quote/conversion interpretation UNVERIFIED"},
               "fees": "Research assumptions: both venues 0bps, then TxFlow taker 4.5bps and Lighter 0bps; rewards excluded.",
               "fee_only_round_trip_breakeven_bps": "9", "entry_threshold_bps": 10, "freshness_ms": 500,
               "txflow_update_interval_median_ms": {c["capture"]: c.get("txflow_update_interval_median_ms") for c in capture_summaries if c.get("integrity") == "VERIFIED_SHA256"},
               "lighter_update_interval_median_ms": {c["capture"]: c.get("lighter_update_interval_median_ms") for c in capture_summaries if c.get("integrity") == "VERIFIED_SHA256"},
               "basis_classification_counts": dict(Counter(row["classification"] for row in quote_rows)),
               "quote_quality_reason_counts": dict(entry_quality),
               "decision_modes": list(MODES), "strategies": list(STRATEGIES), "entry_quality_rejections": dict(entry_quality),
               "limitations": ["Same symbol does not establish identical index or contract economics.", "PnL and size assume a common USDC-equivalent quote and 1:1 BTC size; neither conversion nor economic compatibility is verified.", "Event-driven mode uses only received book events; quote freshness is reevaluated at decisions.", "Capture gaps do not bridge positions across Capture boundaries.", "Holdout results are descriptive and independent only when the Capture is labeled holdout."]}
    summary["execution_aggregates"] = summarize_execution(execution)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    report = ["# Phase 14F — TxFlow x Lighter Core convergence", "",
              "All executions are hypothetical. No rewards are counted as income.", "",
              "## Data and interpretation", "",
              f"Manifest-verified captures: {len([c for c in capture_summaries if c.get('integrity') == 'VERIFIED_SHA256'])}; event-pair rows: {len(quote_rows)}; valid synchronized 500ms rows: {summary['valid_synchronized_500ms']}; 10bps BBO candidates: {summary['valid_bbo_edge_ge_10bps']}.",
              "The Lighter source clock is assumed to be microseconds and clock synchronization is unverified. TxFlow documents full l2Book snapshots with millisecond source time. Lighter market multiplier metadata is not enough to establish contract units or settlement conversion.",
              "Persistent raw spread is therefore only a directional basis candidate. TxFlow publishes full l2Book snapshots on a documented millisecond clock; Lighter snapshot/delta nonce continuity is checked by the reader, while its source clock unit and cross-venue clock synchronization remain unverified. The capture summary retains each venue's update interval, error list, and connection segments. A contract-symbol match does not prove matching index or settlement economics.",
              "", "## Costs", "", "At the assumed TxFlow taker fee of 4.5bps and Lighter 0bps, fee-only round-trip break-even is 9bps before L2 spread and depth impact. Each trade's same-basis executable four-leg L2 cost is listed in breakeven_requirements.csv.", "",
              "## Reproducibility", "", "Replay historical, exploration and holdout captures as separate capture roots. Positions never carry across capture boundaries.", ""]
    report.extend(["", "## Event-driven, 600-second strategy comparison", "",
                   "These counts aggregate independent captures; positions never cross capture boundaries. Fees are hypothetical and rewards are excluded.",
                   "", "| Group | Strategy | Fee | Signals | Paired | Closed (conv/net/stop/timeout) | Censored | Hedge failures | Closed net quote |",
                   "|---|---|---|---:|---:|---:|---:|---:|---:|"])
    for row in summary["execution_aggregates"]:
        if row["decision_mode"] == "event" and row["max_hold_seconds"] == 600:
            report.append(f"| {row['sample_group']} | {row['strategy']} | {row['fee_scenario']} | {row['signals']} | {row['executed_entry_pairs']} | {row['closed']} ({row['convergence_exits']}/{row['net_profit_exits']}/{row['stop_losses']}/{row['timeouts']}) | {row['censored']} | {row['hedge_failures']} | {row['closed_net_pnl_quote']} |")
    (out / "report.md").write_text("\n".join(report))
    print(json.dumps({"captures": len(capture_summaries), "quote_event_pairs": len(quote_rows),
                      "valid_synchronized_500ms": summary["valid_synchronized_500ms"],
                      "bbo_edge_ge_10bps": summary["valid_bbo_edge_ge_10bps"],
                      "execution_scenarios": len(execution), "trades": len(trades_all)}))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--capture-root", type=Path, action="append", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    analyze(args.capture_root, args.output)

if __name__ == "__main__":
    main()
