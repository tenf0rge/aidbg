// Schematic-extracted netlist (analog functional block)
// 2-to-1 pass-gate mux built from tranif switches.
// Pulled in from the symbol library; nets named per schematic.
`celldefine
module analog_mux (
    inout  AOUT,     // shared analog output node
    inout  IN0,      // analog input 0
    inout  IN1,      // analog input 1
    input  SEL0,     // pass-gate 0 enable (control domain)
    input  SEL1      // pass-gate 1 enable (control domain)
);
    // Pass gates extracted from schematic transistors.
    // NOTE: both gates tie onto AOUT. If SEL0 & SEL1 are ever
    // asserted together, IN0 and IN1 fight on AOUT.
    tranif1 (AOUT, IN0, SEL0);
    tranif1 (AOUT, IN1, SEL1);
endmodule
`endcelldefine
