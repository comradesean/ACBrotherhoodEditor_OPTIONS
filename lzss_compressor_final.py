#!/usr/bin/env python3
"""
LZSS Compressor - EXACT 1:1 Implementation
Uses lazy matching to match game encoder perfectly

Implements:
1. Hash chain based match finder (same as game)
2. Cached match length optimization for early termination
3. Lazy matching with exact game adjustment formulas
4. Tiebreaking optimization Scenario 1 (Match-Follow-Match)
"""

# Debug counter for Scenario 1 optimization
scenario1_counter = 0

# Hash chain match finder state (game-accurate implementation)
class HashChainMatchFinder:
    """
    Hash chain based match finder matching game's FUN_01b8de10/FUN_01b8df10.

    Uses same hash function and data structures as the game:
    - 14-bit hash from 3-byte window
    - Hash chain linking positions with same hash
    - Cached match length for early termination optimization
    """

    HASH_SIZE = 16384  # 0x3FFF + 1 (14-bit hash)
    MAX_CHAIN_DEPTH = 2048  # 0x800
    GOOD_ENOUGH_LEN = 2048  # 0x800 - stop searching if match is this long

    def __init__(self, data):
        self.data = data
        self.data_len = len(data)

        # hash_head[hash] = most recent position with this hash (or -1)
        self.hash_head = [-1] * self.HASH_SIZE

        # chain_link[pos] = next older position with same hash (or -1)
        self.chain_link = [-1] * self.data_len

        # Current position being encoded
        self.current_pos = 0

    def _compute_hash(self, pos):
        """
        Compute 14-bit hash from 3 bytes at position.
        Game formula: (((b0 << 5) ^ b1) << 5) ^ b2) * 0x9f5f >> 5) & 0x3fff
        """
        if pos + 2 >= self.data_len:
            return 0

        b0 = self.data[pos]
        b1 = self.data[pos + 1]
        b2 = self.data[pos + 2]

        h = ((b0 << 5) ^ b1)
        h = ((h << 5) ^ b2)
        h = (h * 0x9f5f) >> 5
        h = h & 0x3fff

        return h

    def advance_to(self, pos):
        """
        Advance the hash chain to cover all positions up to pos.
        Must be called sequentially - positions cannot be skipped.
        """
        while self.current_pos < pos:
            # Add current_pos to its hash chain
            if self.current_pos + 2 < self.data_len:
                h = self._compute_hash(self.current_pos)
                # Link to previous head
                self.chain_link[self.current_pos] = self.hash_head[h]
                # Become new head
                self.hash_head[h] = self.current_pos
            self.current_pos += 1

    def find_match(self, pos, max_match_length=2048):
        """
        Find best match at position using hash chain traversal.

        Implements game's early termination conditions:
        1. match_len == max_length (hit limit)
        2. match_len >= GOOD_ENOUGH_LEN (good enough)
        3. match_len > match_len_cache[candidate] (can't do better)
        """
        # Ensure hash chains are built up to this position
        self.advance_to(pos)

        if pos < 2:
            return 0, 0

        # Calculate hash for current position
        h = self._compute_hash(pos)

        # Get head of chain (most recent position with same hash)
        candidate = self.hash_head[h]

        best_length = 0
        best_offset = 0

        max_length = min(max_match_length, self.data_len - pos)
        chain_count = 0

        # Walk the hash chain for 3+ byte matches
        while candidate >= 0 and chain_count < self.MAX_CHAIN_DEPTH:
            chain_count += 1

            # Calculate offset
            offset = pos - candidate

            # Check offset limits (max 8192, and can't reference prefix bytes 0-1)
            if offset > 8192 or candidate < 2:
                candidate = self.chain_link[candidate] if candidate < len(self.chain_link) else -1
                continue

            # Quick rejection: check bytes at best_length-1, best_length, 0, 1
            # Game does: [best-1], [best], [0], [1]
            match_possible = True
            if best_length >= 2:
                if self.data[candidate + best_length - 1] != self.data[pos + best_length - 1]:
                    match_possible = False
                elif candidate + best_length < self.data_len and pos + best_length < self.data_len:
                    if self.data[candidate + best_length] != self.data[pos + best_length]:
                        match_possible = False

            if match_possible:
                if pos + 1 >= self.data_len or candidate + 1 >= self.data_len:
                    match_possible = False
                elif self.data[candidate] != self.data[pos]:
                    match_possible = False
                elif self.data[candidate + 1] != self.data[pos + 1]:
                    match_possible = False

            if match_possible:
                # Extend match
                length = 2
                while (length < max_length and
                       pos + length < self.data_len and
                       candidate + length < self.data_len and
                       self.data[candidate + length] == self.data[pos + length]):
                    length += 1

                if length > best_length:
                    best_length = length
                    best_offset = offset

                    # Early termination 1: hit maximum length
                    if best_length >= max_length:
                        break

                    # Early termination 2: good enough
                    if best_length >= self.GOOD_ENOUGH_LEN:
                        break

                    # Note: Early termination 3 (cached length optimization) was tested
                    # but the game does NOT use it. The game exhaustively searches
                    # the entire hash chain (up to MAX_CHAIN_DEPTH) to find the
                    # longest match, regardless of cached lengths at candidates.

            # Follow chain to older position
            candidate = self.chain_link[candidate] if candidate < len(self.chain_link) else -1

        # If we didn't find a 3+ byte match via hash chain, try to find 2-byte matches
        # The game uses a separate mechanism for 2-byte matches since they require
        # only matching the first 2 bytes, not the same 3-byte hash.
        # Scan backward for 2-byte matches within short match range (offset <= 256)
        if best_length < 2 and pos + 1 < self.data_len:
            b0 = self.data[pos]
            b1 = self.data[pos + 1]

            # Scan back up to 256 positions for 2-byte match
            max_scan = min(256, pos - 2)  # Can't reference prefix (pos 0-1)
            for offset in range(1, max_scan + 1):
                check_pos = pos - offset
                if check_pos < 2:
                    break
                if self.data[check_pos] == b0 and self.data[check_pos + 1] == b1:
                    # Found 2-byte match, now extend it
                    length = 2
                    while (length < max_length and
                           pos + length < self.data_len and
                           check_pos + length < self.data_len and
                           self.data[check_pos + length] == self.data[pos + length]):
                        length += 1

                    if length > best_length:
                        best_length = length
                        best_offset = offset
                        # For 2-byte scan, take first match found (smallest offset)
                        break

        return best_length, best_offset


# Global match finder instance (initialized per compression)
_match_finder = None

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

    The LZSS format supports matches up to ~32KB via extension bytes.
    The game uses matches up to 2048 bytes for highly repetitive SAV file data.

    For length 2048:
      remaining = 2048 - 9 = 2039
      2039 = 7 * 255 + 254
      Encoded as: 7 zero bytes followed by 0xFE
    """
    if pos < 2:
        return 0, 0

    best_length = 0
    best_offset = 0
    second_best_offset = 0
    max_length = min(max_match_length, len(data) - pos)
    max_offset = min(8192, pos)

    # CRITICAL FIX: Reject matches that reference position 0 or 1 (the 2-byte prefix)
    # The game encoder doesn't use matches that go back to the prefix area
    # This typically only affects the very end of files with long runs of zeros
    max_offset = min(max_offset, pos - 2)
    
    # Scan BACKWARD from current position (closer matches found last)
    for check_pos in range(pos - 1, max(0, pos - max_offset) - 1, -1):
        offset = pos - check_pos

        # Quick check: must match at least best_length+1 bytes to be better
        # Check the first and last bytes of potential improvement first
        if best_length >= 2:
            # Check if this position can beat best_length
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
            second_best_offset = best_offset
            best_offset = offset

            # Early termination: if we found max_length match, no need to continue
            if best_length >= max_length:
                break
    
    # NOTE: We return the RAW offset here. The encoder will handle any adjustments needed.
    # Long matches require offset >= 1 (after any encoding adjustment)
    if best_offset > 0 and best_length >= 2:
        is_short_match = (2 <= best_length <= 5 and best_offset <= 256)
        if not is_short_match:
            # Long matches: raw offset must be >= 1 for valid encoding
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

    NOTE: This optimization was DISABLED because it doesn't match game behavior.
    The game takes the full match length without truncation optimization.
    The optimization was incorrectly truncating matches (e.g., 316 bytes to 30 bytes)
    which caused compression mismatches with different save files.

    Returns the original match_length unchanged.
    """
    # DISABLED: Always return the full match length to match game behavior
    return match_length

    # Original (disabled) optimization code below:
    if match_length < 50:  # Only optimize long matches
        return match_length

    # For very long matches (> 500 bytes), don't truncate - the cost-benefit
    # analysis doesn't work well for these. The game uses very long matches
    # for repetitive SAV file data.
    if match_length > 500:
        return match_length

    # Look ahead within the match to find significantly better matches
    # Check positions at various intervals within the match
    best_truncate_at = match_length
    best_savings = 0

    # Current match cost
    current_cost = calculate_match_cost(match_length, match_offset)

    # Check every 10 bytes within the match for better opportunities
    for check_offset in range(10, match_length - 10, 10):
        future_pos = pos + check_offset
        if future_pos >= len(buffered_data):
            break

        # Find best match at this position using hash chain finder
        if _match_finder is not None:
            future_length, future_offset = _match_finder.find_match(future_pos)
        else:
            future_length, future_offset = find_best_match(buffered_data, future_pos)

        if future_length < 50:  # Not a significantly better match
            continue

        # Calculate potential savings
        # Cost of truncating: cost(truncated) + cost(future_match)
        # Cost of not truncating: cost(full_match) + cost(whatever_follows)

        truncated_cost = calculate_match_cost(check_offset, match_offset)
        future_cost = calculate_match_cost(future_length, future_offset)

        # The remaining bytes after our full match would need separate encoding
        remaining_after_full = match_length - check_offset
        remaining_cost_guess = calculate_match_cost(remaining_after_full, match_offset)

        # Compare: truncate + future vs full + remaining
        strategy_truncate = truncated_cost + future_cost
        strategy_full = current_cost + remaining_cost_guess

        # If truncating saves at least 10 bits, do it
        savings = strategy_full - strategy_truncate
        if savings > best_savings and savings >= 10:
            best_savings = savings
            best_truncate_at = check_offset

    return best_truncate_at


def peek_next_decision(buffered_data, pos, curr_length):
    """
    Peek ahead to determine what the next encoding decision will be.

    This is used for Scenario 1 tiebreaking optimization.

    Returns:
        tuple: (is_match, next_length, next_offset) where is_match indicates
               if the next token will be a match (token >= 0x10)
    """
    next_pos = pos + curr_length
    if next_pos >= len(buffered_data):
        return (False, 0, 0)

    # Find best match at next position using hash chain finder
    if _match_finder is not None:
        next_length, next_offset = _match_finder.find_match(next_pos)
    else:
        next_length, next_offset = find_best_match(buffered_data, next_pos)

    # Apply same lazy matching logic as main loop would
    if next_length >= 2 and next_pos + 1 < len(buffered_data):
        if _match_finder is not None:
            lookahead_length, lookahead_offset = _match_finder.find_match(next_pos + 1)
        else:
            lookahead_length, lookahead_offset = find_best_match(buffered_data, next_pos + 1)

        # Determine match types
        next_is_short = (2 <= next_length <= 5 and next_offset <= 256)
        lookahead_is_short = (2 <= lookahead_length <= 5 and lookahead_offset <= 256)

        # Calculate adjustment
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
            next_length = 0  # Would be forced to literal

    if next_length >= 2:
        # Check cost-benefit
        match_cost = calculate_match_cost(next_length, next_offset)
        literal_cost = 9 * next_length
        if match_cost >= literal_cost:
            next_length = 0

    # A match decision means next_length >= 2
    is_match = (next_length >= 2)
    return (is_match, next_length, next_offset)


def compress_lzss_lazy(data):
    """
    Compress using lazy matching (lookahead optimization).
    Uses 2-byte zero prefix - input starts at buffer position 2.

    Implements Scenario 1 tiebreaking optimization:
    - When current match is exactly 3 bytes (length-2 == 1)
    - And previous token exists with bottom 2 bits == 0
    - And next decision will be a match (token >= 0x10)
    - Then: set prev token's bits to 3, encode current as 3 literals
    """
    global scenario1_counter, _match_finder
    scenario1_counter = 0

    # Add 2-byte zero prefix
    buffered_data = bytearray([0x00, 0x00]) + bytearray(data)

    # Initialize hash chain match finder for this compression
    _match_finder = HashChainMatchFinder(buffered_data)

    output = bytearray()
    bit_accum = 0
    bit_counter = 0
    flag_byte_ptr = 0
    decisions = []

    # Track previous match token position for Scenario 1
    # This is the position of byte1 (first byte) of the previous long match,
    # or the offset byte of the previous short match
    prev_token_pos = None
    prev_was_match = False

    # Start at position 2 (after 2-byte prefix)
    pos = 2

    while pos < len(buffered_data):
        # Find best match at current position using hash chain
        curr_length, curr_offset = _match_finder.find_match(pos)
        
        # Force literal at the very first position (game behavior)
        if pos == 2:
            curr_length = 0
        
        # LAZY MATCHING with exact game logic
        if curr_length >= 2 and pos + 1 < len(buffered_data):
            next_length, next_offset = _match_finder.find_match(pos + 1)
            
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
            # Optimize long matches by checking for better opportunities ahead
            curr_length = find_optimal_match_length(buffered_data, pos, curr_length, curr_offset)

        # ===== SCENARIO 1: Match-Follow-Match Optimization =====
        # Conditions from handoff document:
        # 1. Previous token exists
        # 2. Previous token bottom 2 bits == 0
        # 3. Current match length == 3 (encoded as length-2 == 1)
        # 4. Next token >= 0x10 (is a match token)
        # Action: Encode current 3-byte match as 3 literals instead
        #
        # NOTE: The game's assembler shows bit modification (or byte ptr [eax],3)
        # but this may be for internal state tracking rather than modifying output.
        # We skip the bit modification since it corrupts the previous match offset.
        # The key optimization is converting 3-byte match to 3 literals when
        # surrounded by other matches, which can improve subsequent compression.
        scenario1_applied = False
        if curr_length == 3 and prev_was_match and prev_token_pos is not None:
            # Check if previous token has bottom 2 bits == 0
            if (output[prev_token_pos] & 0x03) == 0:
                # Peek ahead to see if next decision will be a match
                next_is_match, _, _ = peek_next_decision(buffered_data, pos, curr_length)
                if next_is_match:
                    # Apply Scenario 1 optimization
                    # Note: We do NOT modify prev_token_pos bits as this corrupts the offset
                    scenario1_applied = True
                    scenario1_counter += 1

                    # Encode all 3 bytes as literals (NOT just the first one)
                    for i in range(3):
                        byte_val = buffered_data[pos + i]
                        decisions.append(('L', byte_val))
                        output, bit_accum, bit_counter, flag_byte_ptr = add_bit(
                            output, bit_accum, bit_counter, flag_byte_ptr, 0
                        )
                        output.append(byte_val)

                    # Clear prev_was_match since we emitted literals
                    prev_was_match = False
                    pos += 3
                    continue  # Skip normal encoding

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
                # Long match
                # NOTE: Long match encoding uses raw offset directly (no -1 like short matches)
                # because the decoder doesn't add +1 for long matches
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

            # Literals don't count as "previous token" for Scenario 1
            # Note: We keep prev_token_pos but clear prev_was_match
            # This matches game behavior where only match tokens are tracked
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
    
    compressed, decisions, s1_count = compress_lzss_lazy(uncompressed)

    print(f"Compressed size: {len(compressed)} bytes ({100*len(compressed)/len(uncompressed):.1f}%)")
    print(f"Decisions: {len(decisions)}")
    print(f"Scenario 1 optimizations applied: {s1_count}")
    
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
