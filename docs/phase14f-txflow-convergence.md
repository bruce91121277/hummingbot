# Phase 14F — TxFlow × Lighter Core 價差與收斂驗證

更新日期：2026-10-29
基準 commit：`d29b84679ed643bcac33ad69322e737e4a3a6ab7`
分類：`HYPOTHETICAL`。以下成交、對沖比率、費率情境與 PnL 均為離線模型結果，不能作為已驗證實盤收益。

## 結論

10bps 以上的 BBO 邊際在本次資料中不是 38,198 個獨立套利機會。它們主要是同一方向、長時間維持的約 10–12bps 跨平台價格差。兩份 30 分鐘 Capture 的中位 Mid Basis 分別是 -11.56bps 與 -11.22bps；有效同步報價的 BBO Edge 中位數分別是 11.47bps 與 11.12bps。

在 500ms freshness/skew gate 後，仍有 40,337 個有效事件配對，其中 38,198 筆記錄顯示 BBO Edge ≥10bps。這些是事件觀察列，不是獨立進場數。兩條合約的標的指數與 Lighter 經濟單位仍未完成驗證，所以價格差目前只能稱為方向性 Basis 候選。

收斂結果沒有支持「可獲利套利」的結論：600 秒 event-driven 情境中，25% Basis 收斂只在探索樣本的 3 個觀察部位中發生 1 次，時間約 278.91 秒；獨立 Holdout 的 3 個部位都沒有在 600 秒內達成 25% 或 50% 收斂。TxFlow 4.5bps、Lighter 0bps 假設下，探索及 Holdout 的四腿 Net Profit > 0 機會均為 0/3。這是小樣本觀察，不能證明未來不會收斂。

## Capture 與回放

五份 Capture 均通過 Manifest 檔案大小及 SHA-256 驗證，沒有被排除。三份歷史 Capture 合計約 658 秒；新增探索與 Holdout 各 1,800 秒，合計觀測時長約 4,257 秒。這些時段彼此獨立，回放不會跨 Capture 延續部位。兩份新 Capture 各自只有一個連線 Segment，Capture errors 為空。

| 樣本 | 觀測秒數 | TxFlow / Lighter 事件數 | TxFlow 更新間隔中位數 / P90 | Lighter 更新間隔中位數 / P90 | 有效同步配對 | BBO Edge ≥10bps |
|---|---:|---:|---:|---:|---:|---:|
| 歷史 1 | 59.43 | 36 / 1,012 | 1,631 / 3,024ms | 51 / 95ms | 280 | 280 |
| 歷史 2 | 299.47 | 262 / 5,247 | 713 / 2,810ms | 51 / 75ms | 2,010 | 2,007 |
| 歷史 3 | 299.44 | 237 / 5,017 | 933 / 3,019ms | 51 / 95ms | 1,791 | 1,779 |
| Exploration | 1,799.60 | 2,485 / 34,758 | 474 / 1,667ms | 50 / 61ms | 19,393 | 18,559 |
| Holdout | 1,799.54 | 2,310 / 33,311 | 477 / 1,917ms | 50 / 64ms | 16,863 | 15,573 |

完整 84,663 個事件配對中，38,198 筆被列為 `DIRECTIONAL_BASIS_CANDIDATE`，44,326 筆為 `STALE_QUOTE_SUSPECT`，2,139 筆為低於門檻或其他未解釋狀態。品質原因計數會重疊，不能相加當成互斥分類。主要的時效問題來自 TxFlow 一側：TxFlow 更新較慢，source/receive age 和跨所 source/receive skew 也常超過 500ms。Lighter 約每 50ms 更新一次，因此更容易和 TxFlow 的舊簿配成不合格的同步列。

事件驅動回放只在實際收到的任一訂單簿事件時重新判斷；另輸出 100ms、250ms、1000ms 對照。輸出保留每列的 Source Timestamp、Oracle receive UTC、Monotonic receive 時間、雙邊年齡、skew、原始時間戳、Lighter nonce、Segment 與品質原因。100ms/250ms/1000ms 不是對缺失行情插值。

## 合約、價格與時鐘證據

TxFlow 官方規格將永續合約描述為線性、每張代表 1 單位標的資產，BTC-USDC 市場 metadata 顯示 base BTC、quote USDC、`currencyType=usdc`。TxFlow 官方 `l2Book` 說明每次推送都是完整簿快照，使用毫秒來源時間；因此本 Capture 沒有為 TxFlow 虛構 sequence。

Lighter Core 本次公開市場 metadata 回傳 BTC、market_id 1、perp、`multiplier=1`、base_asset_id 0、quote_asset_id 0，以及 0bps maker/taker 欄位。這些 metadata 足以辨認所讀取的市場與精度，但尚不足以證明 multiplier 的經濟語意、報價/結算幣別、對 TxFlow 的轉換率或實際帳戶費率。回放因此使用明確標記的 1 BTC 對 1 BTC 假設；沒有宣稱 Delta-neutral。

TxFlow 的價格由其 oracle index 錨定，Lighter Core 的對應標的價格來源與指數籃子尚未在本研究中證明相同。故持續約 11bps 的差值可能是不同參考價格形成的真實 Basis，也可能含有時鐘、更新延遲或市場規格差異；目前資料不能在這些原因之間作出確定判定。

TxFlow source timestamp 是文件說明的毫秒。Lighter `last_updated_at` 按微秒解析才能與本地接收時鐘的數量級相符，但其單位及兩平台時鐘校準仍標記為 UNVERIFIED。來源時間、Oracle 接收 UTC 與 Monotonic clock 是分開分析的；來源時鐘未驗證表示 freshness 結論仍有假設成分。

Lighter Capture 每份均包含 1 個初始 Snapshot，後接 1,011、5,246、5,016、34,757、33,310 個 Delta。Reader 要求更新 nonce 大於前值、delta 的 begin_nonce 等於目前簿 nonce，否則該簿不會被接受；五份資料中每個被計入的 Lighter 事件均通過這項檢查。兩份新增長 Capture 都只有一個 Segment，且 manifest errors 為空。這證明保存事件序列依目前檢查器連續，不等於證明上游協定語意無誤。

## 收斂、費用及右設限

在 600 秒最大觀察下，使用相同 10bps 進場門檻、100ms 假設對沖延遲及 500ms freshness：

| 樣本 | 25% 收斂 | 50% 收斂 | TxFlow 4.5bps 情境已完成交易 Net PnL | 零費率已完成交易 Net PnL | 未完成 |
|---|---:|---:|---:|---:|---:|
| Exploration | 1/3，278.91秒 | 0/3 | -0.235710 quote | +0.034350 quote | 1 |
| Holdout | 0/3 | 0/3 | -0.194045 quote | -0.013959 quote | 1 |
| 歷史 | 0次已觀察；三部位觀察期只有 59–299秒，均右設限 | 同左 | 無已完成退出 | 無已完成退出 | 3 |

探索與 Holdout 的 600 秒 timeout/25% 基準均各有 3 個共同部位；25% 策略探索樣本另有一次收斂退出，並因此多一個新進場訊號。表內 PnL 是該策略中已完成模擬平倉的合計，不含 Capture 結束仍持倉者的未知未來退出費用。未完成部位保留在 `residual_exposure.csv`，使用最後有效可執行估值，並標示估值時間和是否已過時；Capture 結束不會自動平倉。

零費率下，first executable net-positive 檢查在探索及 Holdout 都是 3/3，分別中位約 3.62 秒與 0.78 秒。這些是以 0bps 為前提的即時深度情境，不是 Basis 收斂事件；在 TxFlow 4.5bps 的同一檢查下，探索與 Holdout 都是 0/3。不要把零費率 markout 誤作可支付真實成本的獲利證據。

TxFlow 4.5bps、Lighter 0bps 假設下，四腿純費用損益兩平要求是 9bps。若以進場簿估算完整四腿 L2 VWAP 成本，9 個共同樣本的估計約 9.02–9.93bps。這是假設將同一時刻顯示的深度再用於退出的樂觀估值，未來流動性不保證；它也沒有為 funding 或合約換算未知項目賦零收益。因進場 BBO edge 中位數約 11bps，價差看似足以覆蓋費用的空間只有約 1–2bps，容易被價差變動、深度與延遲抹去。

停止損失設定在 10bps 的情境產生許多止損及負 PnL，顯示固定門檻對持續性 Basis 不能當成收斂保證。未平倉及單腿部位仍留在曝險輸出。500ms 假設 hedge delay 的部分 Capture 發生單腿失敗；輸出的 emergency close 是反事實情境，包含深度與費用，但沒有記成已發生 Fill。

## 為何會有長時間正向差、卻沒有足夠收斂

1. BBO 差值長時間偏向同一方向，較像持續的跨參考價格 Basis，而非反覆的短暫錯價。Capture 只顯示相關性與報價，沒有驗證兩個永續合約跟隨同一組指數。
2. 兩邊更新速度不同。TxFlow 30 分鐘樣本中位約 0.47 秒一筆、P90 約 1.67–1.92 秒；Lighter 中位約 0.05 秒一筆。500ms 門檻過濾掉大量舊簿配對，但來源 clock 仍未完成獨立校準。
3. 10bps 是 BBO 進場條件，並非扣成本的淨收斂門檻。以四腿 L2 VWAP 及 9bps 費用底線後，緩衝太薄；探索只一次 25% 收斂，Holdout 沒有收斂。
4. 退出等待產生右設限及超時部位。歷史短 Capture 的三個部位沒有被當成 600 秒未收斂；它們只觀察到 Capture 結尾，正確保留為右設限。

## 建議與限制

TxFlow 值得保留作為低優先級唯讀觀測路線，但暫不值得投入 Maker、積分或執行策略開發。本輪沒有證據支持在 4.5bps TxFlow 費率下有正淨收益的收斂策略。下一筆工作若要比較 RISEx 與 Nado，建議先將 Nado 作公開行情資料候選：官方 orderbook API 清楚提供 bids/asks、深度及毫秒 timestamp；RISEx 官方頁面雖說 timestamp 預設為奈秒，但頁面標示 WIP、預期短期變更。這只是整合可測性的排序推論，不代表 Nado 有可盈利價差或有效積分。

可重現回放：

```bash
cd ~/perp-arbitrage-hb
.venv-research/bin/python -m basis_convergence.phase14f \
  --capture-root ~/perp-arbitrage/data/phase14e \
  --capture-root ~/perp-arbitrage/data/phase14f/exploration \
  --capture-root ~/perp-arbitrage/data/phase14f/holdout \
  --output outputs/phase14f
```

30 分鐘唯讀 Capture 指令：

```bash
cd ~/perp-arbitrage-hb
.venv-research/bin/python -m basis_convergence.txflow_capture \
  --output-root ~/perp-arbitrage/data/phase14f/exploration \
  --seconds 1800
```

再次採集應使用另一個 output root 作為 Holdout，保持 Capture 獨立。CLI 單次上限 3,600 秒；本輪未跑 3,600 秒，避免在兩份連續 30 分鐘資料無正費率淨收益訊號時無止境延長樣本。

## 官方協定參考

- [TxFlow 合約規格](https://docs.txflow.com/trade/contract-specifications) — 線性永續，每張代表 1 單位底層標的； live precision 仍取決於 market metadata。
- [TxFlow l2Book WebSocket](https://docs.txflow.com/api/websocket/l2Book) — 固定 tick 推送完整簿快照，來源時間為毫秒。
- [TxFlow Mark 與 Oracle 價格](https://docs.txflow.com/trade/mark-and-index-price) — last、mark、oracle 是不同價格，oracle 是外部參考價格錨點。
- [TxFlow 永續市場設定](https://docs.txflow.com/tip/instrument-config) — 市場配置包含 base/quote、精度、費率與 perpetual type。
- [Lighter 官方文件](https://docs.lighter.xyz/) 與 [官方 Python SDK 的 OrderBook schema](https://github.com/elliottech/lighter-python/blob/main/docs/OrderBook.md) — 支援本研究使用的公開市場 metadata 欄位；欄位 `multiplier=1` 本身不足以確定本市場的跨平台經濟換算。
- [Lighter 官方白皮書](https://assets.lighter.xyz/whitepaper.pdf) — 說明 market-specific quote multiplier 參與價格/數量步階到 quote 金額的換算；本報告仍將本市場實際 multiplier 語意標記 UNVERIFIED。
- [Nado Orderbook API](https://docs.nado.xyz/developer-resources/api/v2/orderbook) — 公開簿深度、ticker ID 與毫秒 timestamp。
- [RISEx REST/WebSocket 總覽](https://developer.rise.trade/reference/general-information) — timestamp 欄位預設奈秒；官方頁目前標記 WIP。

## 交付檔案

`outputs/phase14f/` 含逐事件 `quote_quality.csv`、`basis_distribution.csv`、`convergence_survival.csv`、`breakeven_requirements.csv`、`execution_comparison.csv`、`residual_exposure.csv`、逐筆 `convergence_trades.csv.gz`、`summary.json` 和 `report.md`。所有 PnL、非官方合約換算與費率情境都標記為假設研究結果。
