// RTL control block. Generates the pass-gate selects for analog_mux.
// BUG: decode of `chan` is one-hot but the reset/default path
// briefly drives both selects high (overlap), causing IN0/IN1 to
// fight on AOUT in the analog domain.
module ctrl (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [1:0] chan,   // requested channel
    output logic       sel0,
    output logic       sel1
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            // BUG: should be 1'b0 / 1'b0 to disable both gates.
            sel0 <= 1'b1;
            sel1 <= 1'b1;
        end else begin
            sel0 <= (chan == 2'd0);
            sel1 <= (chan == 2'd1);
        end
    end
endmodule
