#!/usr/bin/env python3
"""
LZSS Compression/Decompression Library for AC Brotherhood
==========================================================

This module provides LZSS compression and decompression matching the exact format
used by Assassin's Creed Brotherhood for OPTIONS and SAV files.

This is a single-purpose module for compression/decompression only.
It has no concept of file formats, sections, or serialization.

Main Functions:
    compress(data)     - Compress data using LZSS with lazy matching
    decompress(data)   - Decompress LZSS data

Advanced Functions:
    compress_with_debug(data)  - Returns (compressed, decisions, scenario1_count)
    LZSSDecompressor           - Class-based decompressor with more control

Usage:
    from lzss import compress, decompress

    # Compress data
    compressed = compress(data)

    # Decompress data
    decompressed = decompress(compressed)
"""


# =============================================================================
# DECOMPRESSION
# =============================================================================

class LZSSDecompressor:
    """
    LZSS Decompressor matching AC Brotherhood's exact format.

    LZSS Format:
    - Literal (flag=0): 8-bit byte value
    - Short match (flag=10): 2-bit length (2-5), 8-bit offset (1-256)
    - Long match (flag=11): 3-bit length field + 13-bit offset (0-8191)
    - Terminator: Long match with offset=0 (bytes 0x20 0x00)
    """

    def decompress(self, compressed: bytes) -> bytes:
        """
        Decompress LZSS data.

        Args:
            compressed: Compressed bytes

        Returns:
            Decompressed bytes
        """
        if not compressed:
            return b''

        output = bytearray()
        in_ptr = 0
        flags = 0
        flag_bits = 0

        while in_ptr < len(compressed):
            # Read flag bit
            if flag_bits < 1:
                if in_ptr >= len(compressed):
                    break
                flags = compressed[in_ptr]
                in_ptr += 1
                flag_bits = 8

            flag_bit = flags & 1
            flags >>= 1
            flag_bits -= 1

            if flag_bit == 0:
                # Literal byte
                if in_ptr >= len(compressed):
                    break
                output.append(compressed[in_ptr])
                in_ptr += 1
            else:
                # Match - read second flag bit
                if flag_bits < 1:
                    if in_ptr >= len(compressed):
                        break
                    flags = compressed[in_ptr]
                    in_ptr += 1
                    flag_bits = 8

                flag_bit2 = flags & 1
                flags >>= 1
                flag_bits -= 1

                if flag_bit2 == 0:
                    # Short match (length 2-5, offset 1-256)
                    if flag_bits < 2:
                        if in_ptr >= len(compressed):
                            break
                        flags |= compressed[in_ptr] << flag_bits
                        in_ptr += 1
                        flag_bits += 8

                    length = (flags & 3) + 2
                    flags >>= 2
                    flag_bits -= 2

                    if in_ptr >= len(compressed):
                        break
                    offset_byte = compressed[in_ptr]
                    in_ptr += 1

                    distance = offset_byte + 1
                    src_pos = len(output) - distance

                    for _ in range(length):
                        if src_pos < 0:
                            output.append(0)
                        else:
                            output.append(output[src_pos])
                        src_pos += 1
                else:
                    # Long match (length 3+, offset 0-8191)
                    if in_ptr + 1 >= len(compressed):
                        break

                    byte1 = compressed[in_ptr]
                    byte2 = compressed[in_ptr + 1]
                    in_ptr += 2

                    len_field = byte1 >> 5
                    low_offset = byte1 & 0x1F
                    high_offset = byte2
                    distance = (high_offset << 5) | low_offset

                    # Check for terminator (distance == 0)
                    if distance == 0:
                        break

                    if len_field == 0:
                        # Variable length encoding
                        length = 9
                        while in_ptr < len(compressed) and compressed[in_ptr] == 0:
                            in_ptr += 1
                            length += 255
                        if in_ptr >= len(compressed):
                            break
                        length += compressed[in_ptr]
                        in_ptr += 1
                    else:
                        length = len_field + 2

                    src_pos = len(output) - distance

                    for _ in range(length):
                        if src_pos < 0:
                            output.append(0)
                        else:
                            output.append(output[src_pos])
                        src_pos += 1

        return bytes(output)


def decompress(data: bytes) -> bytes:
    """
    Decompress LZSS data.

    Args:
        data: Compressed bytes

    Returns:
        Decompressed bytes
    """
    decompressor = LZSSDecompressor()
    return decompressor.decompress(data)


# =============================================================================
# COMPRESSION
# =============================================================================

class _HashChainMatchFinder:
    """
    Hash chain based match finder matching game's implementation.

    Uses:
    - 14-bit hash from 3-byte window
    - Hash chain linking positions with same hash
    - Maximum chain depth of 2048 (matches game behavior)
    """

    HASH_SIZE = 16384  # 0x3FFF + 1 (14-bit hash)
    MAX_CHAIN_DEPTH = 2048  # Game appears to use ~2000-2048
    GOOD_ENOUGH_LEN = 2048

    def __init__(self, data):
        self.data = data
        self.data_len = len(data)
        self.hash_head = [-1] * self.HASH_SIZE
        self.chain_link = [-1] * self.data_len
        self.current_pos = 0

    def _compute_hash(self, pos):
        """Compute 14-bit hash from 3 bytes at position."""
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
        """Advance the hash chain to cover all positions up to pos."""
        while self.current_pos < pos:
            if self.current_pos + 2 < self.data_len:
                h = self._compute_hash(self.current_pos)
                self.chain_link[self.current_pos] = self.hash_head[h]
                self.hash_head[h] = self.current_pos
            self.current_pos += 1

    def find_match(self, pos, max_match_length=2048):
        """Find best match at position using hash chain traversal."""
        self.advance_to(pos)

        if pos < 2:
            return 0, 0

        h = self._compute_hash(pos)
        candidate = self.hash_head[h]

        best_length = 0
        best_offset = 0

        max_length = min(max_match_length, self.data_len - pos)
        chain_count = 0

        # Walk hash chain for 3+ byte matches
        while candidate >= 0 and chain_count < self.MAX_CHAIN_DEPTH:
            chain_count += 1

            offset = pos - candidate

            # Check offset limits and prevent self-matches (offset <= 0)
            if offset <= 0 or offset > 8192 or candidate < 2:
                candidate = self.chain_link[candidate] if candidate < len(self.chain_link) else -1
                continue

            # Quick rejection checks
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

                    if best_length >= max_length or best_length >= self.GOOD_ENOUGH_LEN:
                        break

            candidate = self.chain_link[candidate] if candidate < len(self.chain_link) else -1

        # 2-byte match scan for short matches
        if best_length < 2 and pos + 1 < self.data_len:
            b0 = self.data[pos]
            b1 = self.data[pos + 1]

            max_scan = min(256, pos - 2)
            for offset in range(1, max_scan + 1):
                check_pos = pos - offset
                if check_pos < 2:
                    break
                if self.data[check_pos] == b0 and self.data[check_pos + 1] == b1:
                    length = 2
                    while (length < max_length and
                           pos + length < self.data_len and
                           check_pos + length < self.data_len and
                           self.data[check_pos + length] == self.data[pos + length]):
                        length += 1

                    if length > best_length:
                        best_length = length
                        best_offset = offset
                        break

        return best_length, best_offset


def _add_bit(output, bit_accum, bit_counter, flag_byte_ptr, bit_value):
    """Add single bit to output stream."""
    old_bit_counter = bit_counter

    if bit_counter == 0:
        flag_byte_ptr = len(output)
        output.append(0)

    bit_counter += 1
    bit_accum |= (bit_value & 1) << (old_bit_counter & 0x1f)

    if bit_counter > 7:
        output[flag_byte_ptr] = bit_accum & 0xFF
        bit_accum >>= 8
        bit_counter -= 8
        if bit_counter > 0:
            flag_byte_ptr = len(output)
            output.append(0)

    return output, bit_accum, bit_counter, flag_byte_ptr


def _calculate_match_cost(length, offset):
    """Calculate cost in bits for encoding a match."""
    if 2 <= length <= 5 and offset <= 256:
        return 12  # Short match
    elif length < 10:
        return 18  # Long match
    else:
        extra_bytes = (length - 9 + 254) // 255
        return 18 + (extra_bytes * 8)


def compress_with_debug(data: bytes) -> tuple:
    """
    Compress data using LZSS with lazy matching.

    Returns detailed compression information for debugging.

    Args:
        data: Uncompressed bytes

    Returns:
        Tuple of (compressed_bytes, decisions_list, scenario1_count)
        - compressed_bytes: The compressed output
        - decisions_list: List of ('L', byte) or ('M', length, offset) decisions
        - scenario1_count: Number of Scenario 1 optimizations applied
    """
    # Add 2-byte zero prefix
    buffered_data = bytearray([0x00, 0x00]) + bytearray(data)
    match_finder = _HashChainMatchFinder(buffered_data)

    output = bytearray()
    bit_accum = 0
    bit_counter = 0
    flag_byte_ptr = 0
    decisions = []
    pos = 2

    while pos < len(buffered_data):
        curr_length, curr_offset = match_finder.find_match(pos)

        # Force literal at first position
        if pos == 2:
            curr_length = 0

        # Lazy matching
        if curr_length >= 2 and pos + 1 < len(buffered_data):
            next_length, next_offset = match_finder.find_match(pos + 1)

            curr_is_short = (2 <= curr_length <= 5 and curr_offset <= 256)
            next_is_short = (2 <= next_length <= 5 and next_offset <= 256)

            adjustment = 2 if curr_is_short else 1
            if curr_is_short and not next_is_short and next_length >= 2:
                adjustment += 2
            if next_is_short and not curr_is_short:
                adjustment -= 1
            if adjustment < 1:
                adjustment = 1
            if curr_is_short and next_is_short:
                adjustment = 1

            if next_length >= curr_length + adjustment:
                curr_length = 0

        # Cost-benefit check
        if curr_length >= 2:
            match_cost = _calculate_match_cost(curr_length, curr_offset)
            literal_cost = 9 * curr_length
            if match_cost >= literal_cost:
                curr_length = 0

        if curr_length >= 2:
            # Encode match
            decisions.append(('M', curr_length, curr_offset))

            output, bit_accum, bit_counter, flag_byte_ptr = _add_bit(
                output, bit_accum, bit_counter, flag_byte_ptr, 1)

            if 2 <= curr_length <= 5 and curr_offset <= 256:
                # Short match
                output, bit_accum, bit_counter, flag_byte_ptr = _add_bit(
                    output, bit_accum, bit_counter, flag_byte_ptr, 0)

                len_bits = curr_length - 2
                for i in range(2):
                    output, bit_accum, bit_counter, flag_byte_ptr = _add_bit(
                        output, bit_accum, bit_counter, flag_byte_ptr, (len_bits >> i) & 1)

                output.append((curr_offset - 1) & 0xFF)
            else:
                # Long match
                output, bit_accum, bit_counter, flag_byte_ptr = _add_bit(
                    output, bit_accum, bit_counter, flag_byte_ptr, 1)

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

            pos += curr_length
        else:
            # Encode literal
            byte_val = buffered_data[pos]
            decisions.append(('L', byte_val))

            output, bit_accum, bit_counter, flag_byte_ptr = _add_bit(
                output, bit_accum, bit_counter, flag_byte_ptr, 0)
            output.append(byte_val)

            pos += 1

    # Terminator
    output, bit_accum, bit_counter, flag_byte_ptr = _add_bit(
        output, bit_accum, bit_counter, flag_byte_ptr, 1)
    output, bit_accum, bit_counter, flag_byte_ptr = _add_bit(
        output, bit_accum, bit_counter, flag_byte_ptr, 1)

    output.append(0x20)
    output.append(0x00)

    # Flush final bits
    if bit_counter > 0:
        output[flag_byte_ptr] = ((1 << bit_counter) - 1) & bit_accum

    return bytes(output), decisions, 0


def compress(data: bytes) -> bytes:
    """
    Compress data using LZSS with lazy matching.

    Args:
        data: Uncompressed bytes

    Returns:
        Compressed bytes
    """
    compressed, _, _ = compress_with_debug(data)
    return compressed


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description='LZSS Compression/Decompression for AC Brotherhood',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Compress a file:
    python lzss.py compress input.bin output.bin

  Decompress a file:
    python lzss.py decompress input.bin output.bin
""")

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Compress command
    compress_parser = subparsers.add_parser('compress', help='Compress a file')
    compress_parser.add_argument('input', help='Input file')
    compress_parser.add_argument('output', help='Output file')
    compress_parser.add_argument('--compare', '-c', help='File to compare against')

    # Decompress command
    decompress_parser = subparsers.add_parser('decompress', help='Decompress a file')
    decompress_parser.add_argument('input', help='Input file')
    decompress_parser.add_argument('output', help='Output file')

    args = parser.parse_args()

    if args.command == 'compress':
        with open(args.input, 'rb') as f:
            data = f.read()

        print(f"Compressing: {args.input}")
        print(f"Input size: {len(data)} bytes")

        compressed, decisions, s1_count = compress_with_debug(data)

        print(f"Compressed size: {len(compressed)} bytes ({100*len(compressed)/len(data):.1f}%)")
        print(f"Scenario 1 optimizations: {s1_count}")

        if args.compare:
            try:
                with open(args.compare, 'rb') as f:
                    expected = f.read()
                if compressed == expected:
                    print("PERFECT MATCH with comparison file")
                else:
                    print(f"DIFFERS from comparison file ({len(compressed)} vs {len(expected)} bytes)")
            except FileNotFoundError:
                print(f"Comparison file not found: {args.compare}")

        with open(args.output, 'wb') as f:
            f.write(compressed)
        print(f"Wrote: {args.output}")

    elif args.command == 'decompress':
        with open(args.input, 'rb') as f:
            data = f.read()

        print(f"Decompressing: {args.input}")
        print(f"Compressed size: {len(data)} bytes")

        decompressed = decompress(data)

        print(f"Decompressed size: {len(decompressed)} bytes")

        with open(args.output, 'wb') as f:
            f.write(decompressed)
        print(f"Wrote: {args.output}")

    else:
        parser.print_help()
