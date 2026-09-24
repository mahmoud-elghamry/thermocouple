# Placement of the non-channel blocks, in 1.27 mm grid units.
G=1.27
def mm(v): return round(v*G,2)
def spec():
    S={}
    def P(ref,x,y,rot=0): S[ref]=(mm(x),mm(y),rot)
    # ---- isolators: CTRL side left, SENS side right -------------------
    for U,ux,uy,cA,cB in (("U10",276,44,"C41","C42"),("U11",276,84,"C43","C44")):
        P(U,ux,uy); P(cA,ux-7,uy-19,270); P(cB,ux+7,uy-19,90)
    ux,uy=276,44
    for i,R in enumerate(("R25","R26","R36","R37","R38","R39")):   # rows y-6..y+4
        P(R,ux+24+(9 if i%2 else 0),uy-6+2*i,90)
    P("TP5",ux+48,uy-6)
    ux,uy=276,84
    for i,R in enumerate(("R40","R41","R42","R43")):
        P(R,ux+24+(9 if i%2 else 0),uy-6+2*i,90)
    P("R27",ux+24,uy+4,270); P("TP6",ux+48,uy+4)
    # ---- isolated 5 V and the 3.3 V sensor rail ------------------------
    ax,ay=352,30
    P("U12",ax,ay); P("C45",ax-14,ay+1); P("C46",ax+13,ay+1); P("C47",ax+19,ay+1)
    P("U13",ax+34,ay); P("C48",ax+48,ay+1); P("TP4",ax+58,ay-2); P("TP3",ax+58,ay+8)
    # ---- MCU and user interface ----------------------------------------
    ux,uy=260,170
    P("U1",ux,uy)
    P("R28",ux-16,uy-37); P("C52",ux-24,uy-34,270)
    P("Y1",ux-28,uy-14); P("C60",ux-34,uy-11); P("C61",ux-22,uy-11)
    P("C51",ux-17,uy-19)
    P("C49",ux-3,uy-44,270); P("C50",ux+5,uy-44,90)
    P("J2",ux+40,uy-32); P("RV1",ux+28,uy-50); P("R29",ux+30,uy-18,90)
    for i,sw in enumerate(("SW1","SW2","SW3","SW4","SW5")):
        P(sw,ux+18+5*(4-i),uy+42,270)
    P("J5",ux+58,uy-4); P("J6",ux+58,uy+12); P("TP7",ux-30,uy-40)
    # ---- 24 V input, protection, LM5164 buck ----------------------------
    jx,jy=16,236
    P("J1",jx,jy,180)
    P("#FLG1",jx+7,jy+2); P("#FLG2",jx+7,jy)
    P("F1",jx+14,jy+2,90); P("D1",jx+24,jy+2,180); P("#FLG3",jx+29,jy+2)
    P("D2",jx+33,jy+5,270); P("C53",jx+42,jy+5); P("C54",jx+54,jy+5); P("C63",jx+66,jy+5)
    P("R59",jx+78,jy+5); P("R60",jx+78,jy+11)
    ux,uy=jx+100,jy+8
    P("U14",ux,uy); P("R55",ux-16,uy+7)
    P("C62",ux+14,uy-5); P("R58",ux+26,uy-5,180); P("C67",ux+30,uy-8,90); P("L1",ux+34,uy-2,90)
    P("C68",ux+14,uy+5,180); P("R57",ux+22,uy+5); P("R56",ux+30,uy+2,270)
    P("#FLG5",ux+40,uy-2); P("C55",ux+46,uy+1); P("C64",ux+58,uy+1); P("C65",ux+70,uy+1)
    P("TP2",ux+84,uy-2); P("TP1",ux+84,uy+6)
    # ---- RS-485 --------------------------------------------------------
    ux,uy=380,124
    P("U15",ux,uy); P("R33",ux-17,uy-5,180)
    P("C56",ux-28,uy-9); P("C57",ux-36,uy-9)
    P("C58",ux+18,uy-17,180); P("C59",ux+26,uy-17,180); P("#FLG4",ux+18,uy+4)
    X0=ux+36
    P("JP1",X0,uy-10,180); P("R34",X0+9,uy-12,90)
    P("JP2",X0,uy-2,180); P("R35",X0+9,uy-4,90)
    P("JP3",X0,uy+6,180); P("R44",X0+9,uy+4,90)
    P("D5",X0+20,uy+15,270); P("D6",X0+26,uy+15,270)
    P("J4",X0+36,uy-2); P("TP8",X0+36,uy-16); P("TP9",X0+36,uy-12)
    # ---- run-permit relay (coil 2-5, COM 1, NC 4, NO 3) ------------------
    kx,ky=420,180
    P("K1",kx,ky)
    P("D3",kx-11,ky,90); P("R53",kx-14,ky-5); P("R54",kx-14,ky+1)
    P("Q1",kx-20,ky-4); P("R30",kx-30,ky-4,90); P("R31",kx-25,ky-1)
    P("D4",kx+2,ky-12); P("R32",kx+11,ky-12,270)
    P("J3",kx+26,ky)
    return S
