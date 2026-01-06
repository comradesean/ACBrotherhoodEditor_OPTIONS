#!/usr/bin/env python3
"""
LZSS Compressor - Shared Module
================================

EXACT 1:1 implementation matching the game's LZSS compression algorithm.
Uses lazy matching with Scenario 1 tiebreaking optimization.

This module is imported by:
- lzss_compressor_pc.py (standalone CLI tool)
- options_serializer_pc.py (PC OPTIONS file builder)
- options_serializer_ps3.py (PS3 OPTIONS file builder)

Ported from assassinscreedsave project for 1:1 parity.
"""

# Debug counter for Scenario 1 optimization
scenario1_counter = 0


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


def find_best_match(data, pos, max_match_length=2048):
    """
    Find best match scanning backward from current position.
    Data includes 2-byte prefix, pos >= 2.

    Returns RAW offset (no adjustment). Encoder handles any adjustments.
    """
    if pos < 2:
        return 0, 0

    best_length = 0
    best_offset = 0
    max_length = min(max_match_length, len(data) - pos)
    max_offset = min(8192, pos)

    # CRITICAL: Reject matches that reference position 0 or 1 (the 2-byte prefix)
    max_offset = min(max_offset, pos - 2)

    # Scan BACKWARD from current position (closer matches found last)
    for check_pos in range(pos - 1, max(0, pos - max_offset) - 1, -1):
        offset = pos - check_pos

        # Quick check: must match at least best_length+1 bytes to be better
        if best_length >= 2:
            if data[check_pos] != data[pos]:
                continue
            if check_pos + best_length < len(data) and pos + best_length < len(data):
                if data[check_pos + best_length] != data[pos + best_length]:
                    continue

        length = 0
        while (length < max_length and
               pos + length < len(data) and
               data[check_pos + length] == data[pos + length]):
            length += 1

        # Update only if strictly longer (keeps first equal match = highest offset)
        if length > best_length and length >= 2:
            best_length = length
            best_offset = offset

            # Early termination: if we found max_length match, no need to continue
            if best_length >= max_length:
                break

    # Return RAW offset - encoder handles adjustments
    # Long matches require offset >= 1 for valid encoding
    if best_offset > 0 and best_length >= 2:
        is_short_match = (2 <= best_length <= 5 and best_offset <= 256)
        if not is_short_match:
            if best_offset < 1:
                return 0, 0

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


def find_optimal_match_length(buffered_data, pos, match_length, match_offset):
    """
    Find optimal length for a match by looking ahead within it.
    Only applies to matches between 50-500 bytes.
    """
    if match_length < 50:
        return match_length

    if match_length > 500:
        return match_length

    best_truncate_at = match_length
    best_savings = 0
    current_cost = calculate_match_cost(match_length, match_offset)

    for check_offset in range(10, match_length - 10, 10):
        future_pos = pos + check_offset
        if future_pos >= len(buffered_data):
            break

        future_length, future_offset = find_best_match(buffered_data, future_pos)

        if future_length < 50:
            continue

        truncated_cost = calculate_match_cost(check_offset, match_offset)
        future_cost = calculate_match_cost(future_length, future_offset)
        remaining_after_full = match_length - check_offset
        remaining_cost_guess = calculate_match_cost(remaining_after_full, match_offset)

        strategy_truncate = truncated_cost + future_cost
        strategy_full = current_cost + remaining_cost_guess

        savings = strategy_full - strategy_truncate
        if savings > best_savings and savings >= 10:
            best_savings = savings
            best_truncate_at = check_offset

    return best_truncate_at


def peek_next_decision(buffered_data, pos, curr_length):
    """
    Peek ahead to determine what the next encoding decision will be.
    Used for Scenario 1 tiebreaking optimization.

    Returns: (is_match, next_length, next_offset)
    """
    next_pos = pos + curr_length
    if next_pos >= len(buffered_data):
        return (False, 0, 0)

    next_length, next_offset = find_best_match(buffered_data, next_pos)

    # Apply same lazy matching logic as main loop would
    if next_length >= 2 and next_pos + 1 < len(buffered_data):
        lookahead_length, lookahead_offset = find_best_match(buffered_data, next_pos + 1)

        next_is_short = (2 <= next_length <= 5 and next_offset <= 256)
        lookahead_is_short = (2 <= lookahead_length <= 5 and lookahead_offset <= 256)

        if next_is_short:
            adjustment = 2
        else:
            adjustment = 1

        if next_is_short and not lookahead_is_short and lookahead_length >= 2:
            adjustment += 2
        if lookahead_is_short and not next_is_short:
            adjustment -= 1
        if adjustment < 1:
            adjustment = 1
        if next_is_short and lookahead_is_short:
            adjustment = 1

        if lookahead_length >= next_length + adjustment:
            next_length = 0

    if next_length >= 2:
        match_cost = calculate_match_cost(next_length, next_offset)
        literal_cost = 9 * next_length
        if match_cost >= literal_cost:
            next_length = 0

    is_match = (next_length >= 2)
    return (is_match, next_length, next_offset)


def compress_lzss_lazy(data):
    """
    Compress using lazy matching (lookahead optimization).
    Uses 2-byte zero prefix - input starts at buffer position 2.

    Implements Scenario 1 tiebreaking optimization for 1:1 parity with game.

    Returns:
        tuple: (compressed_bytes, decisions_list, scenario1_count)
    """
    global scenario1_counter
    scenario1_counter = 0

    # Add 2-byte zero prefix
    buffered_data = bytearray([0x00, 0x00]) + bytearray(data)

    output = bytearray()
    bit_accum = 0
    bit_counter = 0
    flag_byte_ptr = 0
    decisions = []

    # Track previous match token position for Scenario 1
    prev_token_pos = None
    prev_was_match = False

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

            # Determine match types (using raw offset, boundary at 256)
            curr_is_short = (2 <= curr_length <= 5 and curr_offset <= 256)
            next_is_short = (2 <= next_length <= 5 and next_offset <= 256)

            # Calculate adjustment (from decompiled code logic)
            if curr_is_short:
                adjustment = 2
            else:
                adjustment = 1

            # Adjust based on transition between short/long matches
            if curr_is_short and not next_is_short and next_length >= 2:
                adjustment += 2

            if next_is_short and not curr_is_short:
                adjustment -= 1

            if adjustment < 1:
                adjustment = 1

            # SHORT->SHORT transitions use adjustment=1
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
            # Optimize long matches by checking for better opportunities ahead
            curr_length = find_optimal_match_length(buffered_data, pos, curr_length, curr_offset)

        # ===== SCENARIO 1: Match-Follow-Match Optimization =====
        scenario1_applied = False
        if curr_length == 3 and prev_was_match and prev_token_pos is not None:
            if (output[prev_token_pos] & 0x03) == 0:
                next_is_match, _, _ = peek_next_decision(buffered_data, pos, curr_length)
                if next_is_match:
                    scenario1_applied = True
                    scenario1_counter += 1

                    # Encode all 3 bytes as literals
                    for i in range(3):
                        byte_val = buffered_data[pos + i]
                        decisions.append(('L', byte_val))
                        output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                            output, bit_accum, bit_counter, flag_byte_ptr, 0
                        )
                        output.append(byte_val)

                    prev_was_match = False
                    pos += 3
                    continue

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

                # Track token position for Scenario 1 (offset byte for short matches)
                prev_token_pos = len(output)
                output.append((curr_offset - 1) & 0xFF)
                prev_was_match = True
            else:
                # Long match - uses raw offset directly (no -1)
                output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                    output, bit_accum, bit_counter, flag_byte_ptr, 1
                )

                # Track token position for Scenario 1 (byte1 for long matches)
                prev_token_pos = len(output)

                if curr_length < 10:
                    byte1 = ((curr_length - 2) << 5) | (curr_offset & 0x1F)
                    byte2 = (curr_offset >> 5) & 0xFF
                    output.append(byte1)
                    output.append(byte2)
                else:
                    byte1 = curr_offset & 0x1F
                    byte2 = (curr_offset >> 5) & 0xFF
                    output.append(byte1)
                    output.append(byte2)

                    remaining = curr_length - 9
                    while remaining >= 0xFF:
                        output.append(0)
                        remaining -= 0xFF
                    output.append(remaining & 0xFF)
                prev_was_match = True

            pos += curr_length
        else:
            # Encode literal
            byte_val = buffered_data[pos]
            decisions.append(('L', byte_val))

            output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                output, bit_accum, bit_counter, flag_byte_ptr, 0
            )
            output.append(byte_val)

            prev_was_match = False
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

    return bytes(output), decisions, scenario1_counter


# Convenience function for simple compression (returns only compressed data)
def compress(data):
    """
    Simple compression interface - returns only compressed bytes.

    Args:
        data: Input bytes to compress

    Returns:
        Compressed bytes
    """
    compressed, _, _ = compress_lzss_lazy(data)
    return compressed
