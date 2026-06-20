// Bind-style SVA checkers for the mux output node AOUT.
module checker (input logic clk, input logic aout_known, input logic aout_glitch,
                input logic req, input logic ack);
    // circuit-spec: AOUT must resolve to a known 0/1 when a channel is selected
    chk_aout_known: assert property (@(posedge clk) aout_known)
        else $error("AOUT is X (expected 0/1).");
    // glitch checker: fires if a glitch (short pulse / contention) is seen
    chk_aout_no_glitch: assert property (@(posedge clk) !aout_glitch)
        else $error("glitch on AOUT.");
    // protocol: ack only after req
    chk_handshake_ack: assert property (@(posedge clk) ack |-> $past(req))
        else $error("ack without preceding req.");
endmodule
