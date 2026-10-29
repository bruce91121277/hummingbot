from decimal import Decimal as D

from basis_convergence.capture import Quote
from basis_convergence.engine import NS
from basis_convergence.phase14f import event_pairs, edge_metrics, round_trip_cost


def quote(venue, t, bid, ask):
    return Quote(venue, "BTC", t, t, t // 1000, 1, None, ((D(bid), D(1)),), ((D(ask), D(1)),))


def test_event_pairs_are_deduplicated_and_never_look_ahead():
    left = [quote("txflow", NS, "101", "102"), quote("txflow", 3 * NS, "101", "102")]
    right = [quote("lighter_core", NS, "99", "100"), quote("lighter_core", 2 * NS, "99", "100")]
    pairs = list(event_pairs(left, right))
    assert [(t, a.mono, b.mono) for t, a, b, _ in pairs] == [
        (NS, NS, NS), (2 * NS, NS, 2 * NS), (3 * NS, 3 * NS, 2 * NS)
    ]
    assert all(t >= a.mono and t >= b.mono for t, a, b, _ in pairs)


def test_bid_ask_edge_and_l2_break_even_include_four_legs():
    a = quote("txflow", NS, "101", "102")
    b = quote("lighter_core", NS, "99", "100")
    metrics = edge_metrics(a, b, D(100))
    assert metrics["direction"] == "SHORT_TXFLOW_LONG_LIGHTER"
    assert metrics["best_bbo_edge_bps"] > 0
    qty = D("1")
    cost = round_trip_cost(a, b, "sell", qty, D("4.5"), D(0))
    assert D(cost["fee_only_bps"]) == D(9)
    assert D(cost["same_basis_break_even_bps"]) > D(cost["fee_only_bps"])


def test_invalid_book_pair_is_preserved_for_quality_diagnostics():
    left = [quote("txflow", NS, "101", "102"),
            Quote("txflow", "BTC", 2 * NS, 2 * NS, 0, 1, None, (), ())]
    right = [quote("lighter_core", NS, "99", "100"),
             quote("lighter_core", 2 * NS, "99", "100")]
    pairs = list(event_pairs(left, right))
    assert len(pairs) == 2
    _, a, b, reasons = pairs[-1]
    assert not a.bids
    assert ("left", "ORDERBOOK_INVALID") in reasons
    assert edge_metrics(a, b)["best_bbo_edge_bps"] is None


def test_quote_quality_classifies_clock_and_depth_separately():
    from basis_convergence.phase14f import quote_classification
    metrics = {"l2_vwap_edge_bps": None, "best_bbo_edge_bps": D(12)}
    assert quote_classification([("pair", "SOURCE_SKEW_EXCEEDED")], metrics)[0] == "CLOCK_UNCERTAIN"
    assert quote_classification([], metrics)[0] == "INSUFFICIENT_DEPTH"
    assert "CONTRACT_SPECIFICATION_UNVERIFIED" in quote_classification([], {
        "l2_vwap_edge_bps": D(1), "best_bbo_edge_bps": D(12)
    })[1]


def test_percentiles_use_nearest_rank_for_small_samples():
    from basis_convergence.phase14f import pct
    assert pct([1, 2, 3, 4], 50) == 2
    assert pct([1, 2, 3, 4], 90) == 4


def test_event_driven_replay_observes_convergence_on_received_book_event():
    from basis_convergence.engine import replay
    t0, t1, end = NS, NS + 200_000_000, NS + 400_000_000
    left = [quote("txflow", t0, "101", "101.1"), quote("txflow", t1, "100.1", "100.2")]
    right = [quote("lighter_core", t0, "100", "100.1"), quote("lighter_core", t1, "100", "100.1")]
    _, rows, events = replay("cap", "BTC", left, right, 500, 10, 0, max_hold_s=5,
                             exit_fraction=D(".25"), fee_left=D(0), fee_right=D(0),
                             capture_end_ns=end, decision_ms="event")
    trade = rows[0]
    assert trade["exit_reason"] == "BASIS_CONVERGED"
    assert trade["survival_eligible"] and not trade["right_censored"]
    assert D(trade["entry_basis_bps"]) > 0
    assert D(trade["maximum_basis_widening_bps"]) == 0
    assert trade["first_25_seconds"] == "0.2"
    assert trade["first_50_seconds"] == "0.2"
    assert trade["first_positive_seconds"] == "0.2"
    assert trade["exit_ns"] == t1
    assert [e["time_mono_ns"] for e in events] == sorted(e["time_mono_ns"] for e in events)


def test_event_driven_convergence_without_exit_is_right_censored():
    from basis_convergence.engine import replay
    t0, t1, end = NS, NS + 200_000_000, NS + 400_000_000
    left = [quote("txflow", t0, "101", "101.1"), quote("txflow", t1, "101", "101.1")]
    right = [quote("lighter_core", t0, "100", "100.1"), quote("lighter_core", t1, "100", "100.1")]
    _, rows, _ = replay("cap", "BTC", left, right, 500, 10, 0, max_hold_s=5,
                        capture_end_ns=end, decision_ms="event")
    trade = rows[0]
    assert trade["survival_eligible"] and trade["right_censored"]
    assert trade["exit_ns"] is None and trade["first_25_seconds"] is None
    assert trade["observation_duration_seconds"] == "0.4"


def test_hedge_failure_is_not_counted_as_convergence_survival():
    from basis_convergence.engine import replay
    t0, end = NS, NS + 1_400_000_000
    left = [quote("txflow", t0, "101", "101.1")]
    right = [quote("lighter_core", t0, "100", "100.1")]
    _, rows, _ = replay("cap", "BTC", left, right, 500, 10, 600, max_hold_s=5,
                        capture_end_ns=end, decision_ms="event")
    assert rows[0]["exit_reason"] == "HEDGE_FAILURE"
    assert rows[0]["right_censored"] and not rows[0]["survival_eligible"]


def test_public_capture_duration_is_bounded_before_network_io(tmp_path):
    import asyncio
    import pytest
    from basis_convergence.txflow_capture import main

    with pytest.raises(ValueError, match="duration"):
        asyncio.run(main(tmp_path, 3601))
    assert not list(tmp_path.iterdir())


def test_sampled_replay_does_not_reenter_on_an_unchanged_quote_pair():
    from basis_convergence.engine import replay
    t0 = 10 * NS
    left = [quote("txflow", t0, "101", "101.1")]
    right = [quote("lighter_core", t0, "100", "100.1")]
    _, rows, _ = replay("cap", "BTC", left, right, 500, 10, 0, max_hold_s=.2,
                         fee_left=D(0), fee_right=D(0), capture_end_ns=t0 + 400_000_000,
                         decision_ms=100)
    assert len(rows) == 1
    assert rows[0]["exit_reason"] == "MAX_HOLD_TIMEOUT"

def test_execution_summary_aggregates_counts_and_weights_closed_pnl():
    from basis_convergence.phase14f import summarize_execution
    base = {
        "sample_group": "holdout", "decision_mode": "event", "strategy": "timeout",
        "max_hold_seconds": 600, "fee_scenario": "zero", "signals": 2,
        "first_leg_fills": 2, "executed_entry_pairs": 1, "closed": 1,
        "convergence_exits": 0, "net_profit_exits": 0, "stop_losses": 0,
        "timeouts": 1, "censored": 1, "hedge_failures": 0,
        "closed_net_pnl_quote": "-0.5", "last_open_estimates": ["-1.2"],
    }
    second = {**base, "signals": 1, "first_leg_fills": 1, "executed_entry_pairs": 1,
              "closed": 1, "timeouts": 0, "censored": 0, "closed_net_pnl_quote": "0.1",
              "last_open_estimates": []}
    result = summarize_execution([base, second])[0]
    assert result["signals"] == 3
    assert result["executed_entry_pairs"] == 2
    assert result["censored"] == 1
    assert result["closed_net_pnl_quote"] == "-0.4"
    assert result["mean_closed_net_pnl_quote"] == "-0.2"
    assert result["last_open_estimates_quote"] == ["-1.2"]


def test_write_csv_gzip_round_trips_trade_rows(tmp_path):
    import csv
    import gzip
    from basis_convergence.phase14f import write_csv

    path = tmp_path / "trades.csv.gz"
    write_csv(path, [{"trade_id": "t1", "details": [1, 2]}])
    with gzip.open(path, "rt", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows == [{"trade_id": "t1", "details": "[1, 2]"}]
