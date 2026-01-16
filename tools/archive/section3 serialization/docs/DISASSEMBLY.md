# Disassembly Extracted from SECTION3_SERIALIZATION.md

This document contains raw x86 assembly/disassembly code blocks that were extracted from SECTION3_SERIALIZATION.md to improve readability of the main documentation. The decompiled C code remains in the original document.

**Module Base:** ACBSP = 0x00ae0000
**Ghidra Base:** 0x00400000
**Address Conversion:** WinDbg = Ghidra + 0x6e0000

---

## FUN_01b0a1f0 - Base Class Field Serializer Wrapper

**WinDbg Address:** ACBSP+0x170a1f0 (0x021ea1f0)

This is a thin wrapper that calls FUN_01b12fa0:
```asm
mov eax, [ebp+8]     ; field pointer
mov edx, [ebp+0Ch]   ; property metadata
push eax
push edx
call FUN_01b12fa0
```

---

## FUN_01b124e0 - uint64 Serialization Core

**WinDbg Address:** ACBSP+0x17124e0 (0x021f24e0)
**TTD Position:** B1F2B:1644

**Disassembly Flow:**
```asm
021f24ef  call FUN_01b07940      ; Validation #1
021f24ff  call FUN_01b0d140      ; Validation #2
021f2527  mov esi, [edi+4]       ; Get mode structure
021f252a  mov eax, [esi]         ; Get vtable
021f252c  mov edx, [eax+8]       ; vtable[2] - StartElement
021f252f  push "Value"
021f2536  call edx               ; vtable[2]("Value")
021f253a  mov edx, [eax+7Ch]     ; vtable[0x7c] - uint64 serialize
021f253d  push ebx               ; field pointer
021f2540  call edx               ; vtable[0x7c](field_ptr) <- ACTUAL READ
021f2544  mov edx, [eax+10h]     ; vtable[4] - EndElement
021f2547  push "Value"
021f254e  call edx               ; vtable[4]("Value")
```

---

## FUN_01b48be0 - uint64 VTable Thunk

**WinDbg Address:** ACBSP+0x1748be0 (0x02228be0)
**TTD Position:** B1F2B:1863

Thin wrapper that immediately jumps to FUN_01b496d0:
```asm
02228be0  push ebp
02228be1  mov ebp, esp
02228be3  pop ebp
02228be4  jmp FUN_01b496d0 (022296d0)
```

---

## FUN_01b496d0 - Stream Read/Write (8 bytes - uint64)

**WinDbg Address:** ACBSP+0x17496d0 (0x022296d0)
**TTD Position:** B1F2B:1867

**Traced Execution:**
```asm
B1F2B:186A  cmp [ecx+1010h], 0     ; [0x0a3a16c0] = 0x0003 (not zero)
B1F2B:186C  cmp byte [ecx+4], 0    ; [0x0a3a06b4] = 0x01 (READ mode)
B1F2B:186F  add [ecx+eax*8+8], -8  ; Position pre-decremented by 8
B1F2B:1873  mov ecx, [ecx+8]       ; Get stream object = 0xf6c302d8
B1F2B:1876  mov eax, [eax+18h]     ; vtable[6] = 0x0224f490 (FUN_01b6f490)
B1F2B:1878  jmp eax                ; Jump to actual 8-byte read
```

---

## FUN_01b6f490 - Actual 8-Byte Read

**WinDbg Address:** ACBSP+0x176f490 (0x0224f490)
**TTD Position:** B1F2B:1878

**Traced Execution:**
```asm
B1F2B:187D  mov eax, [esi+18h]     ; Buffer pointer = 0x0a3a0684
B1F2B:187E  mov edx, [eax]         ; Read LOW dword from buffer
B1F2B:187F  mov ecx, [ebp+8]       ; Field pointer = 0xf74c0a68
B1F2B:1880  mov [ecx], edx         ; Write low dword to field
B1F2B:1881  mov eax, [eax+4]       ; Read HIGH dword from buffer
B1F2B:1882  mov [ecx+4], eax       ; Write high dword to field
B1F2B:1883  test [esi+4], 1        ; Endianness check = 0 (no swap needed)
B1F2B:1885  add [esi+18h], 8       ; Advance buffer position by 8
```

---

## CloseSection Backpatch Mechanism

**CloseSection (FUN_01b48920) at 0x02228920**

Traced at TTD position E68A19:CBB for CloseSection("Property"):

```asm
CloseSection("Property") - backpatches base class section size at 0x16

Entry: counter = 3, section name = "Property" (0x02c34c40)

Inside FUN_01b48920:
CBF: movzx eax, [esi+1010h]     ; load counter = 3
CC0: movzx ecx, ax              ; ecx = 3 (for size lookup)
CC1: dec eax                    ; eax = 2 (new counter value)
CC3: mov edi, [esi+ecx*8+8]     ; edi = [esi+0x20] = 0x11 (SIZE = 17 bytes!)
CC5: mov [esi+1010h], ax        ; update counter: 3 -> 2
CC7: mov edx, [edx+50h]         ; inner_vtable[0x50] = 0x0224f090 (seek function)
CC9: mov eax, [esi+eax*8+14h]   ; eax = [esi+0x24] = 0xf08d02f8 (saved POSITION token)
CCA: push eax                   ; push position token
CCB: call inner_vtable[0x50]    ; SEEK back to saved position -> 0x04660016

After seek, stream position is 0x04660016 (offset 0x16):
CD8: mov ecx, [esi+8]           ; load stream object
CDA: mov edx, [eax+34h]         ; inner_vtable[0x34] = 0x0224f4d0 (4-byte write)
CDB: push edi                   ; push size value (0x11 = 17)
CDC: call inner_vtable[0x34]    ; write 4 bytes

Core write at E68A19:CF6:
CF4: mov ecx, [esi+18h]         ; ecx = 0x04660016 (write position)
CF5: mov edx, [eax]             ; edx = 0x00000011 (size value)
CF6: mov [ecx], edx             ; WRITE: [0x04660016] = 0x00000011
CF7: add [esi+18h], 4           ; advance position (but will be restored)
```

---

## FUN_01b0d500 - Single Byte Writer (WRITE Mode Traced)

**WinDbg Address:** 0x021ed500 (Ghidra: 0x01b0d500)
**TTD Position:** E68A19:1A2

**Traced Disassembly:**
```asm
021ed505  mov edi, [ebp+8]       ; param_2 = string name (e.g., "NbClassVersionsInfo" - misleading name!)
021ed508  mov esi, ecx           ; param_1 = serializer (this)
021ed50a  mov eax, [esi]         ; vtable
021ed50c  mov edx, [eax+8]       ; vtable[2] = StartElement
021ed510  call edx               ; StartElement(name) <- NO-OP in WRITE!
021ed512  mov ecx, [ebp+0Ch]     ; param_3 = byte value to write
021ed517  mov edx, [eax+98h]     ; vtable[0x98] = WriteByte
021ed520  call edx               ; WriteByte(value) <- ACTUAL WRITE
021ed524  mov edx, [eax+10h]     ; vtable[4] = EndElement
021ed52a  call edx               ; EndElement(name) <- NO-OP in WRITE!
021ed52f  ret 8
```

---

## LAB_01b6f0b0 - Restore Position (inner_vtable[0x58])

**Ghidra Address:** 0x01b6f0b0 (WinDbg: 0x0224f0b0)

```asm
LAB_01b6f0b0:
    MOV  EAX, [ECX + 0x2c]    ; Get saved offset (relative)
    ADD  EAX, [ECX + 0x14]    ; Add buffer base
    MOV  [ECX + 0x18], EAX    ; Set current position (absolute)
    RET
```

---

## LAB_01b6f010 - IsAtEnd (inner_vtable[0x0c])

**Ghidra Address:** 0x01b6f010 (WinDbg: 0x0224f010)

```asm
LAB_01b6f010:
    MOV  EAX, [ECX + 0x18]    ; current position
    SUB  EAX, [ECX + 0x14]    ; - buffer base = bytes used
    XOR  EDX, EDX
    CMP  EAX, [ECX + 0x1c]    ; compare to capacity
    SETZ DL                    ; DL = 1 if used == capacity
    MOV  AL, DL
    RET
```

---

## FUN_01b48fb0 - TypeInfo Serializer (vtable[0x50])

**WinDbg Address:** 0x02228fb0 (Ghidra: 0x01b48fb0)
**TTD Position:** E68A19:2FA (entry)

**Parameters:**
- ECX (this) = 0x24d476e0 (serializer context)
- [ebp+8] = param_2 = 0x02c1ddec (metadata pointer)
- [ebp+0xC] = param_3 = 0x07a8f6cc -> **0xc9876d66** (type hash)

**Disassembly with Annotations:**
```asm
02228fb0  push    ebp
02228fb1  mov     ebp, esp
02228fb3  push    ecx
02228fb4  push    esi
02228fb5  mov     esi, ecx                    ; esi = serializer context

; FLAG CHECK: Controls whether type NAME string is serialized
02228fb7  cmp     byte ptr [esi+1012h], 0     ; [24d486f2] = 0x00
02228fbe  je      02229008                    ; TAKEN! (flag=0, skip string)

; --- STRING PATH (not taken in this trace) ---
02228fc0  cmp     byte ptr [esi+4], 0         ; Mode check
02228fc4  mov     eax, [esi]                  ; Get vtable
02228fc6  jne     02228fe5                    ; If READ mode, jump

; WRITE mode with string:
02228fc8  mov     edx, [eax+54h]              ; vtable[0x54] = String serializer
02228fcb  lea     ecx, [ebp+8]
02228fce  push    ecx
02228fcf  mov     ecx, esi
02228fd1  call    edx                         ; Serialize type name string
02228fd3  mov     ecx, [ebp+0Ch]
02228fd6  push    ecx
02228fd7  mov     ecx, esi
02228fd9  call    FUN_01b49610                ; Write type hash (4 bytes)
02228fde  pop     esi
02228fdf  mov     esp, ebp
02228fe1  pop     ebp
02228fe2  ret     8

; READ mode with string:
02228fe5  mov     edx, [eax+84h]              ; vtable[0x84]
02228feb  lea     ecx, [ebp-4]
02228fee  push    ecx
02228fef  mov     ecx, esi
02228ff1  mov     [ebp-4], 0
02228ff8  call    edx
02228ffa  mov     ecx, [esi+8]
02228ffd  mov     eax, [ecx]
02228fff  mov     edx, [ebp-4]
02229002  mov     eax, [eax+44h]              ; inner_vtable[0x44]
02229005  push    edx
02229006  call    eax

; --- SIMPLE PATH (taken in this trace) ---
; Just write the type hash, no string
02229008  mov     ecx, [ebp+0Ch]              ; param_3 = &type_hash
0222900b  push    ecx                         ; Push pointer to hash
0222900c  mov     ecx, esi                    ; this = serializer
0222900e  call    FUN_01b49610                ; Write 4-byte type hash
02229013  pop     esi
02229014  mov     esp, ebp
02229016  pop     ebp
02229017  ret     8
```

**Traced Flow:**
```
E68A19:2FA  Entry (ECX=0x24d476e0)
E68A19:2FF  cmp [esi+1012h], 0 -> ZF=1 (flag is 0)
E68A19:300  je 02229008 -> TAKEN
E68A19:301  At 02229008: mov ecx, [ebp+0Ch] -> ECX = 0x07a8f6cc
E68A19:302  push ecx (pointer to type hash)
E68A19:304  call FUN_01b49610
```

---

## FUN_01b49610 - 4-Byte Write Dispatcher

**WinDbg Address:** 0x02229610 (Ghidra: 0x01b49610)
**TTD Position:** E68A19:305 (called from FUN_01b48fb0)

**Parameters:**
- ECX = 0x24d476e0 (serializer context)
- [ebp+8] = 0x07a8f6cc -> **0xc9876d66** (type hash value)

**Disassembly with Annotations:**
```asm
02229610  push    ebp
02229611  mov     ebp, esp

; COUNTER TRACKING CHECK
02229613  cmp     word ptr [ecx+1010h], 0     ; [24d486f0] = 0x0000
0222961b  je      02229645                    ; TAKEN! (counter disabled)

; --- Counter update (skipped) ---
0222961d  cmp     byte ptr [ecx+4], 0         ; Mode check
02229621  je      02229635                    ; WRITE path
; READ: counter -= 4
02229623  movzx   eax, word ptr [ecx+1010h]
0222962a  add     dword ptr [ecx+eax*8+8], -4
0222962f  lea     eax, [ecx+eax*8+8]
02229633  jmp     02229645
; WRITE: counter += 4
02229635  movzx   edx, word ptr [ecx+1010h]
0222963c  add     dword ptr [ecx+edx*8+8], 4
02229641  lea     eax, [ecx+edx*8+8]

; --- ACTUAL I/O OPERATION ---
02229645  cmp     byte ptr [ecx+4], 0         ; [24d476e4] = 0x00 (WRITE)
02229649  mov     ecx, [ecx+8]                ; Get stream object
0222964c  je      02229656                    ; TAKEN (WRITE mode)

; READ path: inner_vtable[0x1c]
0222964e  mov     eax, [ecx]
02229650  mov     eax, [eax+1Ch]              ; inner_vtable[7] = 4-byte read
02229653  pop     ebp
02229654  jmp     eax

; WRITE path: inner_vtable[0x34]
02229656  mov     eax, [ebp+8]                ; param = &value
02229659  mov     edx, [ecx]                  ; Get inner vtable
0222965b  mov     eax, [eax]                  ; Dereference: EAX = actual value
0222965d  mov     edx, [edx+34h]              ; inner_vtable[0x34] = 4-byte write
02229660  push    eax                         ; Push VALUE (not pointer!)
02229661  call    edx                         ; Call FUN_01b6f4d0 -> FUN_01b6fea0
02229663  pop     ebp
02229664  ret     4
```

---

## FUN_01b0d140 - Property Header Writer (Key Assembly Points)

**WinDbg Address:** 0x021ed140 (Ghidra: 0x01b0d140)
**TTD Position:** E68A1B:25B (first property write)

**Key Assembly Points:**
```asm
021ed190  push    offset "Property"    ; String for section name
021ed196  call    edx                  ; vtable[0x0c] = OpenSection
          ; -> Reserves 4 bytes at current position for size

021ed19b  mov     eax, [ebx+4]         ; Get property hash from metadata
021ed1af  call    FUN_01b0e680         ; Write property hash (4 bytes)
          ; -> Writes hash to buffer

021ed1c7  mov     edx, [ebx+8]         ; type_info low
021ed1ca  mov     eax, [ebx+0Ch]       ; type_info high
021ed1da  call    FUN_01b0e980         ; Write type_info (8 bytes)
          ; -> Writes 8-byte type descriptor

021ed2a4  and     al, 0EFh             ; Clear bit 4
021ed2a6  or      al, 0Bh              ; Set flags to 0x0b
021ed2ac  call    FUN_01b076f0         ; Write flags byte
          ; -> Writes single byte 0x0b to buffer
```

---

## FUN_01b48e80 - Bool Serializer (vtable[0x58])

**WinDbg Address:** 0x02228e80 (Ghidra: 0x01b48e80)
**TTD Position:** E68A1B:411

**Disassembly:**
```asm
02228e80  push    ebp
02228e81  mov     ebp, esp
02228e83  pop     ebp
02228e84  jmp     FUN_01b497f0 (022297f0)
```

---

## FUN_01b48be0 - uint64 Serializer (vtable[0x7c]) - WRITE Mode

**WinDbg Address:** 0x02228be0 (Ghidra: 0x01b48be0)
**TTD Position:** E68A1D:3EE

**Disassembly:**
```asm
02228be0  push    ebp
02228be1  mov     ebp, esp
02228be3  pop     ebp
02228be4  jmp     FUN_01b496d0 (022296d0)
```

---

## FUN_01b6ff10 - 8-Byte Write Core (inner_vtable[0x30])

**Ghidra Address:** 0x01b6ff10

**Decompiled:**
```c
void __thiscall FUN_01b6ff10(int param_1, undefined4 *param_2)
{
  undefined4 *puVar1;

  // Buffer capacity check
  if (*(int *)(param_1 + 0x30) != 0) {
    if (*(uint *)(param_1 + 0x1c) < (*(int *)(param_1 + 0x18) - *(int *)(param_1 + 0x14)) + 8U) {
      FUN_01b6f1b0(((*(int *)(param_1 + 0x18) - *(uint *)(param_1 + 0x1c)) -
                   *(int *)(param_1 + 0x14)) + 8);
    }
  }
  // Byte swap if needed
  if ((*(byte *)(param_1 + 4) & 1) != 0) {
    FUN_01b4a240(param_2);
  }
  // Write 8 bytes (two uint32s)
  puVar1 = *(undefined4 **)(param_1 + 0x18);
  *puVar1 = *param_2;
  puVar1[1] = param_2[1];
  *(int *)(param_1 + 0x18) = *(int *)(param_1 + 0x18) + 8;
  return;
}
```

**Key points:**
- Writes 8 bytes as two consecutive uint32s
- Buffer position at `[stream+0x18]`, advances by 8
- Optional byte swap via FUN_01b4a240 for endianness

---

## FUN_01b076f0 - Property Flags Writer (PropertyHeaderFlag)

**Ghidra Address:** 0x01b076f0

**Decompiled:**
```c
void __thiscall FUN_01b076f0(int param_1, byte *param_2)
{
  int *piVar1;
  byte *pbVar2;
  undefined4 uStack_8;

  pbVar2 = param_2;
  uStack_8 = param_1;

  // Version > 10: Write single byte via vtable[0x98]
  if (10 < *(int *)(param_1 + 0x24)) {
    piVar1 = *(int **)(param_1 + 4);
    (**(code **)(*piVar1 + 8))("PropertyHeaderFlag");
    (**(code **)(*piVar1 + 0x98))(param_2);
    (**(code **)(*piVar1 + 0x10))("PropertyHeaderFlag");
    return;
  }

  // Legacy version <= 10: Write separate "Final" and "Owned" bits
  piVar1 = *(int **)(param_1 + 4);
  param_2 = (byte *)(CONCAT13(*param_2, param_2._0_3_) & 0x1ffffff);
  (**(code **)(*piVar1 + 8))("Final");
  (**(code **)(*piVar1 + 0x58))((int)&param_2 + 3);
  (**(code **)(*piVar1 + 0x10))("Final");
  *pbVar2 = *pbVar2 ^ (*pbVar2 ^ param_2._3_1_) & 1;

  piVar1 = *(int **)(param_1 + 4);
  uStack_8 = CONCAT13(*pbVar2 >> 1, (undefined3)uStack_8) & 0x1ffffff;
  (**(code **)(*piVar1 + 8))("Owned");
  (**(code **)(*piVar1 + 0x58))((int)&uStack_8 + 3);
  (**(code **)(*piVar1 + 0x10))("Owned");
  *pbVar2 = *pbVar2 ^ (uStack_8._3_1_ * '\x02' ^ *pbVar2) & 2;
  return;
}
```

**Key points:**
- Writes the 0x0b flags byte for properties
- Version > 10 (our case, version=16): Single byte write via vtable[0x98]
- Legacy path writes "Final" and "Owned" bits separately
- Flags byte 0x0b = bits 0,1,3 set (Final=1, Owned=1, bit3=1)
