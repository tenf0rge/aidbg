// UVM scoreboard: compares DUT AOUT against the reference model.
class scoreboard extends uvm_scoreboard;
    `uvm_component_utils(scoreboard)

    uvm_analysis_imp #(mux_item, scoreboard) ap;
    bit [0:0] expected;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void write(mux_item t);
        // line 13: mismatch report
        if (t.aout !== expected)
            `uvm_error("MISCMP", $sformatf("AOUT mismatch: exp=%0d got=%0b", expected, t.aout))
        if (t == null)
            // line 17: null transaction guard (fires on bad TLM wiring)
            `uvm_fatal("TLM", "null transaction handle")
    endfunction
endclass
