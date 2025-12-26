#!/usr/bin/env python3
"""
LZSS Compressor - EXACT 1:1 Implementation
Uses lazy matching to match game encoder perfectly
"""

def add_bit(output, bit_accum, bit_counter, flag_byte_ptr, bit_value):
    """Add single bit - exact Ghidra implementation"""
    old_bit_counter = bit_counter
    
    if bit_counter == 0:
        flag_byte_ptr = len(output)
        output.append(0)
    
    bit_counter += 1
    bit_accum |= (bit_value & 1) << (old_bit_counter & 0x1f)
    
    if (bit_counter > 7):
        output[flag_byte_ptr] = bit_accum & 0xFF
        bit_accum >>= 8
        bit_counter -= 8
        if bit_counter > 0:
            flag_byte_ptr = len(output)
            output.append(0)
    
    return output, bit_accum, bit_counter, flag_byte_ptr

def find_best_match(data, pos):
    """
    Find best match scanning backward from current position.
    Data includes 2-byte prefix, pos >= 2.
    """
    if pos < 2:
        return 0, 0

    best_length = 0
    best_offset = 0
    second_best_offset = 0
    max_length = min(263, len(data) - pos)
    max_offset = min(8192, pos)

    # CRITICAL FIX: Reject matches that reference position 0 or 1 (the 2-byte prefix)
    # The game encoder doesn't use matches that go back to the prefix area
    # This typically only affects the very end of files with long runs of zeros
    max_offset = min(max_offset, pos - 2)
    
    # Scan BACKWARD from current position (closer matches found last)
    for check_pos in range(pos - 1, max(0, pos - max_offset) - 1, -1):
        offset = pos - check_pos
        length = 0
        
        while (length < max_length and 
               pos + length < len(data) and
               data[check_pos + length] == data[pos + length]):
            length += 1
        
        # Update only if strictly longer (keeps first equal match = highest offset)
        if length > best_length and length >= 2:
            best_length = length
            second_best_offset = best_offset
            best_offset = offset
    
    # Game adds +1 to LONG match offsets only, requires final offset >= 2
    if best_offset > 0 and best_length >= 2:
        is_short_match = (2 <= best_length <= 5 and (best_offset + 1) <= 256)
        if not is_short_match:
            best_offset += 1
            # Only reject offset < 2 for LONG matches (short matches allow offset=1 for RLE)
            if best_offset < 2:
                return 0, 0  # Reject if final offset < 2
    
    return best_length, best_offset

def calculate_match_cost(length, offset):
    """Calculate cost in bits for encoding a match"""
    if 2 <= length <= 5 and offset <= 256:
        # Short match: 1 flag + 1 type + 2 length + 8 offset = 12 bits
        return 12
    elif length < 10:
        # Long match: 1 flag + 1 type + 16 data = 18 bits
        return 18
    else:
        # Very long match with continuation bytes
        extra_bytes = (length - 9 + 254) // 255
        return 18 + (extra_bytes * 8)

def compress_lzss_lazy(data):
    """
    Compress using lazy matching (lookahead optimization).
    Uses 2-byte zero prefix - input starts at buffer position 2.
    """
    # Add 2-byte zero prefix
    buffered_data = bytearray([0x00, 0x00]) + bytearray(data)
    
    output = bytearray()
    bit_accum = 0
    bit_counter = 0
    flag_byte_ptr = 0
    decisions = []
    
    # Start at position 2 (after 2-byte prefix)
    pos = 2
    
    while pos < len(buffered_data):
        # Find best match at current position
        curr_length, curr_offset = find_best_match(buffered_data, pos)
        
        # Force literal at the very first position (game behavior)
        if pos == 2:
            curr_length = 0
        
        # LAZY MATCHING with exact game logic  
        if curr_length >= 2 and pos + 1 < len(buffered_data):
            next_length, next_offset = find_best_match(buffered_data, pos + 1)
            
            # Determine match types
            curr_is_short = (2 <= curr_length <= 5 and curr_offset <= 256)
            next_is_short = (2 <= next_length <= 5 and next_offset <= 256)
            
            # Calculate adjustment (from decompiled code logic)
            if curr_is_short:
                adjustment = 2
            else:
                adjustment = 1
            
            # Adjust based on transition between short/long matches
            if curr_is_short and not next_is_short and next_length >= 2:
                adjustment += 2  # local_10 = 2

            if next_is_short and not curr_is_short:
                adjustment -= 1

            if adjustment < 1:
                adjustment = 1

            # SHORT→SHORT transitions use adjustment=1
            if curr_is_short and next_is_short:
                adjustment = 1

            # Compare: if next_length >= curr_length + adjustment, use literal (lazy)
            if next_length >= curr_length + adjustment:
                curr_length = 0  # Force literal
        
        if curr_length >= 2:
            # Check if match is worth encoding (vs literal)
            match_cost = calculate_match_cost(curr_length, curr_offset)
            literal_cost = 9 * curr_length  # 1 flag bit + 8 data bits per byte

            if match_cost >= literal_cost:
                # Match is not beneficial, use literal (prefer literals when costs equal)
                curr_length = 0
        
        if curr_length >= 2:
            # Encode match
            decisions.append(('M', curr_length, curr_offset))
            
            # Flag bit 1
            output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                output, bit_accum, bit_counter, flag_byte_ptr, 1
            )
            
            if 2 <= curr_length <= 5 and curr_offset <= 256:
                # Short match
                output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                    output, bit_accum, bit_counter, flag_byte_ptr, 0
                )
                
                len_bits = curr_length - 2
                for i in range(2):
                    output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                        output, bit_accum, bit_counter, flag_byte_ptr, (len_bits >> i) & 1
                    )
                
                output.append((curr_offset - 1) & 0xFF)
            else:
                # Long match
                output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                    output, bit_accum, bit_counter, flag_byte_ptr, 1
                )
                
                if curr_length < 10:
                    byte1 = ((curr_length - 2) << 5) | ((curr_offset - 1) & 0x1F)
                    byte2 = ((curr_offset - 1) >> 5) & 0xFF
                    output.append(byte1)
                    output.append(byte2)
                else:
                    byte1 = (curr_offset - 1) & 0x1F
                    byte2 = ((curr_offset - 1) >> 5) & 0xFF
                    output.append(byte1)
                    output.append(byte2)
                    
                    remaining = curr_length - 9
                    while remaining >= 0xFF:
                        output.append(0)
                        remaining -= 0xFF
                    output.append(remaining & 0xFF)
            
            pos += curr_length
        else:
            # Encode literal
            byte_val = buffered_data[pos]
            decisions.append(('L', byte_val))
            
            output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                output, bit_accum, bit_counter, flag_byte_ptr, 0
            )
            output.append(byte_val)
            
            pos += 1
    
    # Terminator
    output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
        output, bit_accum, bit_counter, flag_byte_ptr, 1
    )
    output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
        output, bit_accum, bit_counter, flag_byte_ptr, 1
    )
    
    output.append(0x20)
    output.append(0x00)
    
    # Flush final bits
    if bit_counter > 0:
        output[flag_byte_ptr] = ((1 << bit_counter) - 1) & bit_accum
    
    return bytes(output), decisions

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='LZSS Compressor with lazy matching')
    parser.add_argument('input', nargs='?', default='./lzss_uncompressed.bin',
                        help='Input file to compress (default: ./lzss_uncompressed.bin)')
    parser.add_argument('output', nargs='?', default='./lzss_compressed.bin',
                        help='Output compressed file (default: ./lzss_compressed.bin)')
    parser.add_argument('--compare', '-c', default='./compressed_compare.bin',
                        help='File to compare against (default: ./compressed_compare.bin)')
    parser.add_argument('--decisions', '-d', default='./compression_decisions.txt',
                        help='Output file for compression decisions (default: ./compression_decisions.txt)')
    
    args = parser.parse_args()
    
    with open(args.input, 'rb') as f:
        uncompressed = f.read()
    
    print(f"Compressing: {args.input}")
    print(f"Input size: {len(uncompressed)} bytes")
    
    compressed, decisions = compress_lzss_lazy(uncompressed)
    
    print(f"Compressed size: {len(compressed)} bytes ({100*len(compressed)/len(uncompressed):.1f}%)")
    print(f"Decisions: {len(decisions)}")
    
    # Compare with game
    try:
        with open(args.compare, 'rb') as f:
            game_output = f.read()
        
        print(f"Game output: {len(game_output)} bytes")
        
        if compressed == game_output:
            print("\n🎯🎯🎯 PERFECT 1:1 MATCH! 🎯🎯🎯")
        else:
            diff_bytes = len(compressed) - len(game_output)
            print(f"\nSize difference: {diff_bytes:+d} bytes")
            
            # Find first difference
            for i in range(min(len(compressed), len(game_output))):
                if compressed[i] != game_output[i]:
                    print(f"First diff at byte {i}: ours=0x{compressed[i]:02x}, game=0x{game_output[i]:02x}")
                    break
    
    except FileNotFoundError:
        print(f"\nComparison file not found: {args.compare}")
    
    # Save output
    with open(args.output, 'wb') as f:
        f.write(compressed)
    
    with open(args.decisions, 'w') as f:
        for dec in decisions:
            if dec[0] == 'L':
                f.write(f"L:{dec[1]:02x}\n")
            else:
                f.write(f"M:{dec[1]},{dec[2]}\n")
    
    print(f"\nSaved compressed output to: {args.output}")
    print(f"Saved decisions to: {args.decisions}")
