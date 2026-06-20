// UVM monitor: samples AOUT and publishes transactions.
class mux_monitor extends uvm_monitor;
    `uvm_component_utils(mux_monitor)

    virtual mux_if vif;
    uvm_analysis_port #(mux_item) ap;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    task run_phase(uvm_phase phase);
        forever begin
            @(posedge vif.clk);
            // line 15: sampling point
            if (vif.aout === 1'bx)
                `uvm_warning("SAMPLE", "sampled X on AOUT")
        end
    endtask
endclass
