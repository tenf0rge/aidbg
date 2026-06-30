# skill: reg-data-mismatch（レジスタread不一致：DUTかTBか）

## いつ効くか
UVM スコアボードが**レジスタ read の不一致**で落ちる
（例: `[SCB_CMP] MISMATCH for Addr=... Expected=... Got=...`）。
同じ「不一致」でも、**DUTが誤データを返した（DESIGN）**のか、**バスは正しいのに
TBが取り違えた（VERIFICATION-ENV）**のかを切り分ける。

## 背景知識（核心）
**「TBの主張より、波形上の実バス値を信じる」**。スコアボードの Got は TB が
モニタ経由で取得した値で、ここ自体が壊れていることがある。判定は必ず
**実際のバス波形（APB なら `prdata`）を、readが完了したサイクルで**読んで行う。
APB read 完了は `psel=1 & penable=1 & pwrite=0 & pready=1` のサイクル。

## 手順
1. `grep-log --severity ERROR` で各 MISMATCH の **Addr / Expected / Got** を取得。
2. `env --log <L>` で UVM 構成（driver/monitor/scoreboard）と test/sequence を把握。
3. 各不一致アドレスについて、**read が完了するサイクル**を波形で特定する：
   `query --signal pready`（と pwrite/psel/penable）で `pready=1 & pwrite=0` の時刻 T を探す。
   ※ read 発行サイクルと**完了サイクルを取り違えない**こと（よくある誤り）。
4. その T で `query --signal prdata --time T` を読み、**バス上の実データ**を得る。
5. バス実値を Expected / Got と突き合わせて判定（下表）。
6. DESIGN 判定なら、その値を駆動する RTL を `find-driver`/`grep-source`→`blame` で
   「誰のどのコミット」に遡る。

## Design / Verification-env の判定
| 観測 | 判定 | 意味 |
|---|---|---|
| バス実値 == Got（≠ Expected） | **DESIGN** | DUT がバス上に誤データを出した。モニタは正しく拾えている |
| バス実値 == Expected（≠ Got） | **VERIFICATION-ENV** | バスは正しいのに scoreboard/monitor が取り違えた |
| バス実値がどちらとも違う | UNKNOWN | サンプリング時刻/アドレス対応をさらに精査 |

TB側バグの典型機序：モニタ→スコアボードのハンドル by-reference 共有で clone 漏れ、
FIFO/キューの取り違え、未初期化の sentinel 値との比較、サンプリング位相ずれ。

## 例（samples/apb：run.log + wave.csv）
2件の SCB_CMP MISMATCH：
- **0x1000**: Expected A5A5B6B6 / Got DEADDEAD。read 完了サイクルで
  `query prdata` → **DEADDEAD**（＝Got）。バスに誤データ → **DESIGN**（DUTバグ）。
- **0x1004**: Expected 12345678 / Got BADC0DE1。read 完了サイクルで
  `query prdata` → **12345678**（＝Expected）。バスは正しい → **VERIFICATION-ENV**
  （scoreboard が取り違え）。

→ 一見同じ2件の不一致が、実は **DUT側バグ**と**TB側バグ**の混在。レポートでは
2件を別レイヤとして切り分け、TB側は検証チーム、DUT側は設計チームへ、と振り分ける。
