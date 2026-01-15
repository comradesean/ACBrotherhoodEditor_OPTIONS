#pragma once

#include <QByteArray>
#include <cstdint>

namespace acb {

class LZSS {
public:
    // Compress data using lazy matching with Scenario 1 optimization
    // Must match game's exact algorithm for round-trip compatibility
    static QByteArray compress(const QByteArray& data);

    // Decompress LZSS data
    static QByteArray decompress(const QByteArray& compressed);

private:
    // Compression state for bit-level operations
    struct CompressState {
        QByteArray output;
        int bitAccum = 0;
        int bitCounter = 0;
        int flagBytePtr = 0;
        int prevTokenPos = -1;
        bool prevWasMatch = false;
    };

    // Add single bit to output
    static void addBit(CompressState& state, int bitValue);

    // Find best match at position (data includes 2-byte prefix)
    static std::pair<int, int> findBestMatch(const QByteArray& data, int pos, int maxMatchLength = 2048);

    // Calculate cost in bits for encoding a match
    static int calculateMatchCost(int length, int offset);

    // Find optimal length for a match by looking ahead
    static int findOptimalMatchLength(const QByteArray& data, int pos, int matchLength, int matchOffset);

    // Peek ahead to determine next encoding decision (for Scenario 1)
    static std::tuple<bool, int, int> peekNextDecision(const QByteArray& data, int pos, int currLength);
};

} // namespace acb
