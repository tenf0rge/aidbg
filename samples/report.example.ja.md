# aidbg デバッグレポート

**入力**
- wave: `samples/wave.txt`
- netlist: `samples/analog_mux.v`
- log: `samples/uvm.log`
- registry: `samples/assertions.json`
- source: `samples`
- repo: `/home/yuki/projects/aidbg`

**5 件の指摘**（確信度順）。

## 1. AOUT で tranif 競合 → X
- **レイヤ**: 設計（DESIGN）  ·  **確信度**: 90%  ·  **スキル**: `tranif-contention`

**観測されたエラー**

ノード 'AOUT' が t=35ns で X 化。シム/アサーションが多重ドライブの strength 競合を検出。

**真因（最重要）**

制御 (SEL0, SEL1) が同時にアサートされ、2 個のパスゲートが同時導通。競合するアナログ入力が 'AOUT' で衝突し strength 競合 → X。真因はイネーブルの重なりを許している制御ロジック。

**作り込み元（git blame）**

- コミット `6aa18a403bd4` — tenf0rge（2026-06-20）
  - Initial commit: aidbg MVP with triage skill and sample scenario
  - 作り込み箇所: `samples/ctrl.sv:15`

**根拠**

- [t=35ns, net=tb.dut.u_mux.AOUT] AOUT が X 化
- [t=35ns, `samples/analog_mux.v:15`] tranif1 が導通（制御 SEL0=オン）、IN0=St0 を駆動
- [t=35ns, `samples/analog_mux.v:16`] tranif1 が導通（制御 SEL1=オン）、IN1=St1 を駆動
- [`samples/ctrl.sv:15`] SEL0 の駆動: sel0 <= 1'b1;
- [`samples/ctrl.sv:18`] SEL0 の駆動: sel0 <= (chan == 2'd0);
- [`samples/fixture/bug/ctrl.sv:14`] SEL0 の駆動: sel0 <= 1'b1;
- [`samples/fixture/bug/ctrl.sv:17`] SEL0 の駆動: sel0 <= (chan == 2'd0);
- [`samples/fixture/design/rtl/ctrl.sv:12`] SEL0 の駆動: sel0 <= 1'b0;
- [`samples/fixture/design/rtl/ctrl.sv:15`] SEL0 の駆動: sel0 <= (chan == 2'd0);
- [`samples/ctrl.sv:16`] SEL1 の駆動: sel1 <= 1'b1;
- [`samples/ctrl.sv:19`] SEL1 の駆動: sel1 <= (chan == 2'd1);
- [`samples/fixture/bug/ctrl.sv:15`] SEL1 の駆動: sel1 <= 1'b1;
- [`samples/fixture/bug/ctrl.sv:18`] SEL1 の駆動: sel1 <= (chan == 2'd1);
- [`samples/fixture/design/rtl/ctrl.sv:13`] SEL1 の駆動: sel1 <= 1'b0;
- [`samples/fixture/design/rtl/ctrl.sv:16`] SEL1 の駆動: sel1 <= (chan == 2'd1);

**修正提案（提案のみ・未適用）**

- 対象: `samples/ctrl.sv:15`
- SEL0, SEL1 を相互排他（one-hot）にする。リセット/デフォルトで全イネーブルを非活性にし、パスゲートが重ならないようにする。


## 2. グリッチ 'chk_aout_no_glitch' は実グリッチ（設計）
- **レイヤ**: 設計（DESIGN）  ·  **確信度**: 80%  ·  **スキル**: `glitch-triage`

**観測されたエラー**

グリッチチェッカ 'chk_aout_no_glitch' が t=35ns で発火。

**真因（最重要）**

t=35ns に 'AOUT' で物理的な競合/X が併発 → 設計起因の実グリッチ（駆動ロジックは tranif-contention の指摘を参照）。

**根拠**

- [t=35ns] グリッチチェッカ発火
- [t=35ns, net=AOUT] 共有ノードの競合/X

**修正提案（提案のみ・未適用）**

- 制御ロジックの競合の真因を修正する。グリッチチェッカは実設計欠陥を正しく報告している。


## 3. UVM ERROR [NOITEM] @ uvm_test_top.env.agent.seqr
- **レイヤ**: 検証環境（VERIFICATION-ENV）  ·  **確信度**: 65%  ·  **スキル**: `uvm-env`

**観測されたエラー**

response fifo empty（t=95ns）

**真因（最重要）**

エラーは stimulus/transport 経路に由来 → 検証環境側の欠陥の可能性が高い（sequence/driver/TLM 結線）。

**根拠**

- [t=95ns, `./tb/seq/mux_seq.sv:33`] response fifo empty

**修正提案（提案のみ・未適用）**

- 対象: `./tb/seq/mux_seq.sv:33`
- sequence/driver を点検: アイテム生成、レスポンス処理、TLM ポート接続。


## 4. UVM ERROR [MISCMP] @ uvm_test_top.env.sb
- **レイヤ**: 不明（UNKNOWN）  ·  **確信度**: 45%  ·  **スキル**: `uvm-env`

**観測されたエラー**

AOUT mismatch: exp=1 got=x（t=40ns）

**真因（最重要）**

チェッカが報告した不一致 — 症状であり真因ではない。期待値と実値を DESIGN 出力まで辿り、別途、参照/期待値そのものの正しさ（TB）も確認する。

**根拠**

- [t=40ns, `./tb/env/scoreboard.sv:142`] AOUT mismatch: exp=1 got=x

**修正提案（提案のみ・未適用）**

- 対象: `./tb/env/scoreboard.sv:142`
- 不一致時刻で DUT 出力と参照モデルを突き合わせ、予測器（predictor）を検証する。


## 5. UVM FATAL [TLM] @ uvm_test_top.env.sb
- **レイヤ**: 不明（UNKNOWN）  ·  **確信度**: 45%  ·  **スキル**: `uvm-env`

**観測されたエラー**

null transaction handle（t=100ns）

**真因（最重要）**

チェッカが報告した不一致 — 症状であり真因ではない。期待値と実値を DESIGN 出力まで辿り、別途、参照/期待値そのものの正しさ（TB）も確認する。

**根拠**

- [t=100ns, `./tb/env/scoreboard.sv:150`] null transaction handle

**修正提案（提案のみ・未適用）**

- 対象: `./tb/env/scoreboard.sv:150`
- 不一致時刻で DUT 出力と参照モデルを突き合わせ、予測器（predictor）を検証する。

