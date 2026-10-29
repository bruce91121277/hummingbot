# Reward eligibility and venue evidence

Reviewed 2026-10-29 UTC. VERIFIED_ACTIVE means the official page currently describes an active season; it does not establish a wallet's eligibility or the value of points. Point weights are not public for several programs, so no point value is assigned.

| Venue | Status | Eligibility facts |
|---|---|---|
| TxFlow | VERIFIED_ACTIVE | Season 1 began 2026-10-12, distributes 1,250,000 trader points weekly and concludes no later than Q1 2027. It evaluates overall trading quality, including fees, slippage/negative markouts, volume and open interest/hold; activity solely for farming may earn fewer or no points. [Official points rules](https://docs.txflow.com/points/how-points-work) |
| RISEx | VERIFIED_ACTIVE | RISE Points Season 1 Ignite has been live since 2026-07-20, allocates 200,000 points weekly and ends no later than Q2 2027. Qualifying factors include trading sophistication, costs, maker/taker volume, open interest/hold time and referrals; weights may change and are unpublished. [Official season announcement](https://blog.risechain.com/rise-points-season-1-ignite-everything-you-need-to-know/) |
| Arcus | VERIFIED_ACTIVE | Official Arcus Points announcement describes Season 1, a 250,000 weekly pool, and trade, market making, retained deposits and referral activities; season end is no later than H1 2027. Individual eligibility/weights are not fully established by this review. [Official announcement](https://arcus.xyz/blog/introducing-arcus-points) |
| Nado | VERIFIED_ACTIVE | Current official Season 2 page is labeled Live, says it began 2026-05-21, has open access, and distributes a 300,000-950,000 weekly pool based on trading activity adjusted by fee tier and toxicity. The page states no end date. [Official Season 2 page](https://docs.nado.xyz/incentives-and-rewards/points/season-2-live.md) |
| Lighter Core / Lighter RH | UNKNOWN | This review did not verify a currently active official rewards program for either instance. Treat Core and RH as separate deployments; do not transfer market data or eligibility assumptions between them. [Lighter docs](https://docs.lighter.xyz/); [Robinhood Lighter domains](https://docs.robinhood.com/chain/lighter-domains/) |

## Fee and market evidence

TxFlow publishes VIP0 perpetual fees of 1.5 bps maker and 4.5 bps taker, charges fees per side in USDC, and documents linear contracts of one underlying unit. Its BTC perpetual is BTC-USDC. Its public `l2Book` feed sends full snapshots with millisecond timestamps. [Fees](https://docs.txflow.com/trade/fees); [Contract specs](https://docs.txflow.com/trade/contract-specifications); [L2 feed](https://docs.txflow.com/api/websocket/l2Book)

RISEx publishes Tier 1 base fees of 1.0 bps maker and 3.0 bps taker in its fee documentation; its market docs list BTC/USDC. Those are venue schedule values, not account-verified rates. [Official fee docs](https://docs.risechain.com/docs/risex/trading/fees); [Official markets docs](https://docs.risechain.com/docs/risex/trading/markets)

Nado publishes entry-tier fees of 1.0 bps maker and 3.5 bps taker; fee tiers can provide maker rebates. Its BTC perpetual product and USDT0 settlement are documented. Exact funding cadence, market metadata and contract multiplier still need direct capture/evidence. [Official fee docs](https://docs.nado.xyz/core/fees-and-rebates.md); [Products](https://docs.nado.xyz/core/products); [Public API subscriptions](https://docs.nado.xyz/developer-resources/api/subscriptions.md)

Arcus fee schedule, funding rules, contract multiplier and settlement currency remain UNKNOWN in this evidence set. The existing Arcus x Lighter RH captures show ticker overlap only; they do not establish matching economic contracts.

No point allocation is treated as cash or as a trading-cost offset.
