* Custom Spice Netlist

.SUBCKT D n3 m3 o3 vcc vss
* INOUT vcc vss
* INPUT n3 m3
* OUTPUT o3
M1 gd1 n3 vcc vcc PMOS W=1u L=0.5u
M2 gd1 m3 vcc vcc PMOS W=1u L=0.5u
M3 gd1 n3 vss vss NMOS W=1u L=0.5u
M4 gd1 m3 vss vss NMOS W=1u L=0.5u
M5 gd2 n3 vcc vcc PMOS W=1u L=0.5u
M6 gd2 m3 vcc vcc PMOS W=1u L=0.5u
M7 gd2 n3 vss vss NMOS W=1u L=0.5u
M8 gd2 m3 vss vss NMOS W=1u L=0.5u
M9 o3 gd1 vcc vcc PMOS W=1u L=0.5u
M10 o3 gd2 vcc vcc PMOS W=1u L=0.5u
M11 o3 gd1 vss vss NMOS W=1u L=0.5u
M12 o3 gd2 vss vss NMOS W=1u L=0.5u
.ENDS

.SUBCKT C n2 m2 o2 vcc vss
* INOUT vcc vss
* INPUT n2 m2
* OUTPUT o2 dummy_o
Xid1 n2 m2 o2 vcc vss D
Xid2 m2 n2 dummy_o vcc vss D
.ENDS

.SUBCKT B n1 o1 xo1 vcc vss
* INOUT vcc vss
* INPUT n1
* OUTPUT o1 xo1
M1 nonpinb n1 vcc vcc PMOS W=1u L=0.5u
M2 o1 nonpinb vcc vcc PMOS W=1u L=0.5u
M3 o1 n1 vss vss NMOS W=1u L=0.5u
M4 xo1 n1 vss vss NMOS W=1u L=0.5u
Xic n1 nonpinb o1 vcc vss C
.ENDS

.SUBCKT A n0 oa1 oa2 vcc vss
* INOUT vcc vss
* INPUT n0
* OUTPUT oa1 oa2
Xib n0 oa1 oa2 vcc vss B
.ENDS

.SUBCKT mycell in1 in2 out1 out2 out3 out4 vcc vss
* INOUT vcc vss
* INPUT in1 in2
* OUTPUT out1 out2 out3 out4
Xia1 in1 out1 out2 vcc vss A
Xia2 in2 out3 out4 vcc vss A
.ENDS
