// UVM sequence: drives channel-select stimulus.
class mux_seq extends uvm_sequence #(mux_item);
    `uvm_object_utils(mux_seq)

    function new(string name = "mux_seq");
        super.new(name);
    endfunction

    task body();
        mux_item it;
        // line 11: pull response (empty if driver never returned an item)
        get_response(it);
        if (it == null)
            `uvm_error("NOITEM", "response fifo empty")
    endtask
endclass
