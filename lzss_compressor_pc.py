#!/usr/bin/env python3
"""
LZSS Compressor CLI - PC Version
=================================

Command-line interface for LZSS compression using the shared lzss module.
Uses lazy matching to match game encoder perfectly.

Usage:
    python lzss_compressor_pc.py input.bin [output.bin]
"""

from lzss import compress_lzss_lazy, compress


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
            print("\n PERFECT 1:1 MATCH!")
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
