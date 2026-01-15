# Visual Diagrams for Section 3 Serialization

These visual diagrams were extracted from [SECTION3_SERIALIZATION.md](SECTION3_SERIALIZATION.md) for easier reference.

---

## Visual: Section Nesting and Backpatching (Consolidated)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               SECTION NESTING WITH LIFO BACKPATCHING (WRITE MODE)           │
└─────────────────────────────────────────────────────────────────────────────┘

FILE LAYOUT WITH NESTED SECTIONS:
─────────────────────────────────
Offset   Content                          Nesting
0x00     Section 3 header
0x0e     [SIZE placeholder] ──────────────┬── OBJECT SECTION (outermost)
0x12     [SIZE placeholder] ──────────────┼──┬── PROPERTIES SECTION
0x16     [SIZE placeholder] ──────────────┼──┼──┬── BASECLASS SECTION (innermost)
0x1a     Base class (17 bytes)            │  │  │
0x2b     Properties...                    │  │  └── ends at 0x2b
0x9e     Dynamic props (4 bytes)          │  └───── ends at 0xa2
0xa2     EOF                              └──────── ends at 0xa2


STACK-BASED SIZE CALCULATION:
─────────────────────────────
OpenSection reserves 4 bytes and pushes position to stack.
CloseSection pops position, calculates size, seeks back, writes size, seeks forward.

  Formula: size = current_position - saved_position - 4

  Stack grows during OpenSection:     Stack shrinks during CloseSection:
  ┌─────────────────────────────┐     ┌─────────────────────────────────────────┐
  │ [2] pos=0x16 (BaseClass)    │     │ Pop 0x16: size=0x2b-0x16-4=17  (first)  │
  │ [1] pos=0x12 (Properties)   │     │ Pop 0x12: size=0xa2-0x12-4=136 (second) │
  │ [0] pos=0x0e (Object)       │     │ Pop 0x0e: size=0xa2-0x0e-4=144 (last)   │
  └─────────────────────────────┘     └─────────────────────────────────────────┘


BACKPATCHING SEQUENCE (LIFO order):
───────────────────────────────────
  Position:   0x0e      0x12      0x16      0x1a                    0xa2
              │         │         │         │                        │
  Initial:    │ ????    │ ????    │ ????    │◄── content written ──►│
              │         │         │         │                        │
  Step 5:     │ ????    │ ????    │  17  ◄──┼── FIRST backpatch     │
              │         │         │         │   (cursor at 0x2b)     │
  Step 7:     │ ????    │ 136  ◄──┼─────────┼── SECOND backpatch    │
              │         │         │         │   (cursor at 0xa2)     │
  Step 8:     │ 144  ◄──┼─────────┼─────────┼── THIRD backpatch     │
              │         │         │         │   (cursor at 0xa2)     │
              ▼         ▼         ▼         ▼                        ▼
  Final:    ┌─────────┬─────────┬─────────┬──────────────────────────┐
            │ 144     │ 136     │ 17      │   serialized data        │
            │ Object  │ Props   │ Base    │   (base + properties)    │
            └─────────┴─────────┴─────────┴──────────────────────────┘

  Verified TTD positions: 0x16←E68A19:CF7, 0x12←E68A1D:B87, 0x0e←E68A1F:D0
```

---

## Visual: Single Property Section Nesting

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              PROPERTY SECTION (Each Property Has Its Own Section)           │
└─────────────────────────────────────────────────────────────────────────────┘

For each property, the same OpenSection/CloseSection pattern is used:

  FUN_01b0d140 (Property Header Writer):
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                                                                          │
  │   1. OpenSection("Property")                                             │
  │      ├─ Reserve 4 bytes for size at current position                     │
  │      └─ Push position to section stack                                   │
  │                                                                          │
  │   2. Write hash (4 bytes)          ─┐                                    │
  │   3. Write type_info (8 bytes)      │  Property header                   │
  │   4. Write flags (1 byte)          ─┘  (13 bytes fixed)                  │
  │                                                                          │
  │   [Return to caller - caller writes value]                               │
  │                                                                          │
  │   5. Write value (variable size depending on type)                       │
  │                                                                          │
  │   6. CloseSection("Property")                                            │
  │      ├─ Pop position from stack                                          │
  │      ├─ Calculate size = current_pos - saved_pos - 4                     │
  │      └─ Backpatch size at saved position                                 │
  │                                                                          │
  └──────────────────────────────────────────────────────────────────────────┘


  Example: bool_field_0x20 (first property after base class)

  Before CloseSection:
  ┌────────────┬────────────┬──────────────┬───────┬───────┐
  │ size(????) │ hash       │ type_info    │ flags │ value │
  │ 4 bytes    │ 0x3b546966 │ 8 bytes      │ 0x0b  │ 0x01  │
  └────────────┴────────────┴──────────────┴───────┴───────┘
  │            │◄───────────── 14 bytes ─────────────────►│
  ▲
  saved_pos

  After CloseSection:
  ┌────────────┬────────────┬──────────────┬───────┬───────┐
  │ size = 14  │ hash       │ type_info    │ flags │ value │
  │ 0x0000000e │ 0x3b546966 │ 8 bytes      │ 0x0b  │ 0x01  │
  └────────────┴────────────┴──────────────┴───────┴───────┘
       ▲
       │
       └─── Backpatched with calculated size
```
