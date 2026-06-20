// Top-level testbench: instantiates the mixed-signal DUT and the UVM env.
module tb_top;
    logic clk = 0, rst_n = 0;
    logic [1:0] chan;
    always #5 clk = ~clk;

    // DUT: RTL control + extracted analog netlist
    wire AOUT, IN0, IN1, SEL0, SEL1;
    ctrl       u_ctrl (.clk, .rst_n, .chan, .sel0(SEL0), .sel1(SEL1));
    analog_mux u_mux  (.AOUT, .IN0, .IN1, .SEL0, .SEL1);

    initial begin
        rst_n = 0; #15 rst_n = 1;
        #200 $finish;
    end
endmodule
