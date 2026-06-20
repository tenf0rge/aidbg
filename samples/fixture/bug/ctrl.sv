// RTL control block: generates one-hot pass-gate selects for analog_mux.
// BUG version (hotfix): reset forces BOTH selects high. Intended to remove an
// X on AOUT during reset, but it instead turns both pass gates on, so IN0 and
// IN1 fight on AOUT -> strength conflict -> X.
module ctrl (
    input  logic       clk,
    input  logic       rst_n,
    input  logic [1:0] chan,
    output logic       sel0,
    output logic       sel1
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sel0 <= 1'b1;
            sel1 <= 1'b1;
        end else begin
            sel0 <= (chan == 2'd0);
            sel1 <= (chan == 2'd1);
        end
    end
endmodule
