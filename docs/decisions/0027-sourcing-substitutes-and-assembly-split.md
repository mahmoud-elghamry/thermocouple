# 0027 — Three sourcing substitutes, technician fits the through-hole parts, three boards

* Status: accepted
* Date: 2026-10-01
* Deciders: owner ("اعمل توصياتك"; technician for THT; 3 boards)
* Relates to: `I-078`, `I-069`, `0024`

## Context

Five BOM lines had no LCSC code and were found under the exact MPN, or as the
same part on a reel: U2-U9, U13, U15, U1 and RV1 (see I-078). Three could not
be found that way.

## Decision

| Ref | Was | Now | Why |
|---|---|---|---|
| K1 | Omron G5LE-1 DC24 | **Omron G5LE-14 DC24**, LCSC `C116965` | G5LE-1 is not at LCSC. The Omron datasheet lists -14 as the "fully sealed" version of the same SPDT relay: same terminals, same footprint. Rejected: G5LE-1-VD DC24, of which only 5 are in stock. |
| C53 | Panasonic EEUFC2A220 | **Rubycon 100YXF22MEFC8X11.5**, LCSC `C88838` | Not at LCSC. The replacement is the same rating (22 uF, 100 V, 105 °C, 8 mm, 3.5 mm pitch), from a known maker, with 11.8 k in stock. Rejected: the cheapest no-name parts. |
| U12 | XP Power IA0505S | **XP Power IA0505S, unchanged; bought at DigiKey** (`1470-1345-5-ND`), hand-fitted | LCSC only has other makers' "IA0505S-1W..." parts, which are the I-069 trap. The XP part is in production (lifecycle "Production") and stocked at DigiKey. |

**Assembly split:** the factory fits the SMD parts. The technician fits every
through-hole part:

* relay, terminal blocks, DIP socket, headers, buttons;
* IA0505S, C53, RV1, LED, test points.

The owner said this is easy for the technician. The factory THT option is
worth taking only if the quote shows the price difference is small.

**Quantity:** 3 boards, one per 8-channel module (`0024`).

## Consequences

* K1's value changed to G5LE-14 DC24. The netlist baseline was revised for that
  value only; connectivity is unchanged.
* The C53 catalog entry now names the Rubycon part.
* U12 needs a DigiKey order (and customs) separate from the fab order. Order it
  early.
