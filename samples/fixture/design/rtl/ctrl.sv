// RTL control block: generates one-hot pass-gate selects for analog_mux.
// GOOD version: reset drives both selects inactive, decode is one-hot.
module ctrl (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [1:0] chan,
    output logic       sel0,
    output logic       sel1
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sel0 <= 1'b0;
            sel1 <= 1'b0;
        end else begin
            sel0 <= (chan == 2'd0);
            sel1 <= (chan == 2'd1);
        end
    end
endmodule
