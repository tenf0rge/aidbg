# skill: uvm-env（UVM ERROR/FATAL をコンポーネント役割で切り分け）

## いつ効くか
UVM の ERROR/FATAL が出たが、それが**検証環境固有の問題**（ドライバ/シーケンサ/
コンフィグ）なのか、**設計の不具合の兆候**（スコアボード不一致など）なのかを、
発報した**コンポーネントの役割**から一次切り分けしたいとき。

## 背景知識
- ログの `file(line)` が `uvm_pkg.sv` を指していても、それは **UVMマクロの位置**で
  あって真の発生箇所ではない。**blame 対象にしない**。真の場所はメッセージ本文／
  コンポーネント階層から辿る。
- コンポーネント役割の目安：
  - **scoreboard / ref-model**：不一致は「症状」。真因は DUT か、その手前の monitor/TB。
    → 単独で結論を出さず、`reg-data-mismatch` 等で実バスと突き合わせる。
  - **driver / sequencer**：プロトコル違反/スタベーション/コンフィグ不整合は
    **VERIFICATION-ENV** 寄り。
  - **monitor**：サンプリング位相・プロトコル解釈ミスは **VERIFICATION-ENV**。ただし
    monitor が正しく拾った「DUTの異常」を報告している場合は DESIGN の兆候。

## 手順
1. `grep-log --severity ERROR`（と FATAL）で発報コンポーネント・ID・本文を取得。
2. `env --log <L>` で UVM コンポーネント階層と test/sequence を把握し、発報者の役割を確定。
3. 役割で一次仕分け（上表）。scoreboard 由来なら必ず波形へ降りて実値で確認
   （`reg-data-mismatch` / `tranif-contention` / `glitch-triage` に接続）。
4. 真の発生箇所が RTL/TB ソースなら `grep-source`→`find-driver`→`blame` で
   「誰のどのコミット」に遡る（`uvm_pkg.sv` は除外）。

## Design / Verification-env の判定
- 役割と実証（波形/ソース）が DUT の異常を指す → **DESIGN**。
- ドライバ/シーケンサ/モニタ/コンフィグの不整合に帰着 → **VERIFICATION-ENV**。
- scoreboard 単独では決めない（症状であり真因ではない）。

## 例（samples/apb：run.log）
`UVM_ERROR ... env.scb [SCB_CMP] MISMATCH ...` が2件。発報は **scoreboard**＝症状。
file は `uvm_pkg.sv(220)`（マクロ位置）なので blame しない。`reg-data-mismatch` に
接続し、実バス `prdata` と突き合わせて 0x1000=DESIGN / 0x1004=VERIFICATION-ENV に分ける。
