# aidbg デバッグレポート

**入力**
- wave: `samples/apb/wave.csv`
- log: `samples/apb/run.log`

**4 件の指摘**（確信度順）。

## 1. 32'h0000_1000 のリードデータ不一致
- **レイヤ**: 設計（DESIGN）  ·  **確信度**: 85%  ·  **スキル**: `reg-data-mismatch`

**観測されたエラー**

scoreboard が 32'h0000_1000 でリードデータ不一致を報告: 期待 32'hA5A5_B6B6、観測 32'hDEAD_DEAD。

**真因（最重要）**

波形上、32'h0000_1000 のリード時にバスは prdata=deaddead を示しており、scoreboard の観測値と一致・期待値と相違。DUT が誤データを返している → 設計バグ。

**根拠**

- [t=95ns, net=tb_top.dut.prdata] scoreboard: 期待 32'hA5A5_B6B6、観測 32'hDEAD_DEAD
- [t=90ns, net=tb_top.dut.prdata] 32'h0000_1000 リード時のバス prdata=deaddead（t=90ns）

**修正提案（提案のみ・未適用）**

- 32'h0000_1000 の DUT リードデータ経路／レジスタデコードを点検。


## 2. 32'h0000_1004 のリードデータ不一致
- **レイヤ**: 検証環境（VERIFICATION-ENV）  ·  **確信度**: 80%  ·  **スキル**: `reg-data-mismatch`

**観測されたエラー**

scoreboard が 32'h0000_1004 でリードデータ不一致を報告: 期待 32'h1234_5678、観測 32'hBADC_0DE1。

**真因（最重要）**

波形上、32'h0000_1004 のリード時にバスは prdata=12345678（＝期待値）を示している。バスは正しく、scoreboard/monitor 側が取り違え／期待値が誤り → 検証環境バグ。

**根拠**

- [t=115ns, net=tb_top.dut.prdata] scoreboard: 期待 32'h1234_5678、観測 32'hBADC_0DE1
- [t=110ns, net=tb_top.dut.prdata] 32'h0000_1004 リード時のバス prdata=12345678（t=110ns）

**修正提案（提案のみ・未適用）**

- monitor のサンプリング点（pready/penable 整合）と scoreboard の期待モデルを確認。


## 3. UVM ERROR [SCB_CMP] @ uvm_test_top.env.scb
- **レイヤ**: 不明（UNKNOWN）  ·  **確信度**: 40%  ·  **スキル**: `uvm-env`

**観測されたエラー**

MISMATCH for Addr=32'h0000_1000. Expected=32'hA5A5_B6B6 Got=32'hDEAD_DEAD（t=95ns）

**真因（最重要）**

UVM コンポーネントのエラー。報告元コンポーネントを特定し、設計か TB かを判断する。

**根拠**

- [t=95ns] MISMATCH for Addr=32'h0000_1000. Expected=32'hA5A5_B6B6 Got=32'hDEAD_DEAD

**修正提案（提案のみ・未適用）**

- 報告元コンポーネントとそのデータ源を特定する。


## 4. UVM ERROR [SCB_CMP] @ uvm_test_top.env.scb
- **レイヤ**: 不明（UNKNOWN）  ·  **確信度**: 40%  ·  **スキル**: `uvm-env`

**観測されたエラー**

MISMATCH for Addr=32'h0000_1004. Expected=32'h1234_5678 Got=32'hBADC_0DE1（t=115ns）

**真因（最重要）**

UVM コンポーネントのエラー。報告元コンポーネントを特定し、設計か TB かを判断する。

**根拠**

- [t=115ns] MISMATCH for Addr=32'h0000_1004. Expected=32'h1234_5678 Got=32'hBADC_0DE1

**修正提案（提案のみ・未適用）**

- 報告元コンポーネントとそのデータ源を特定する。

