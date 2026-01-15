#include "LZSS.h"
#include <tuple>
#include <algorithm>

namespace acb {

void LZSS::addBit(CompressState& state, int bitValue)
{
    int oldBitCounter = state.bitCounter;

    if (state.bitCounter == 0) {
        state.flagBytePtr = state.output.size();
        state.output.append(static_cast<char>(0));
    }

    state.bitCounter += 1;
    state.bitAccum |= (bitValue & 1) << (oldBitCounter & 0x1f);

    if (state.bitCounter > 7) {
        state.output[state.flagBytePtr] = static_cast<char>(state.bitAccum & 0xFF);
        state.bitAccum >>= 8;
        state.bitCounter -= 8;
        if (state.bitCounter > 0) {
            state.flagBytePtr = state.output.size();
            state.output.append(static_cast<char>(0));
        }
    }
}

std::pair<int, int> LZSS::findBestMatch(const QByteArray& data, int pos, int maxMatchLength)
{
    if (pos < 2) {
        return {0, 0};
    }

    int bestLength = 0;
    int bestOffset = 0;
    int maxLength = std::min(maxMatchLength, static_cast<int>(data.size()) - pos);
    int maxOffset = std::min(8192, pos);

    // Reject matches that reference position 0 or 1 (the 2-byte prefix)
    maxOffset = std::min(maxOffset, pos - 2);

    // Scan BACKWARD from current position (closer matches found last)
    for (int checkPos = pos - 1; checkPos >= std::max(0, pos - maxOffset); --checkPos) {
        int offset = pos - checkPos;

        // Quick check: must match at least bestLength+1 bytes to be better
        if (bestLength >= 2) {
            if (data[checkPos] != data[pos]) {
                continue;
            }
            if (checkPos + bestLength < data.size() && pos + bestLength < data.size()) {
                if (data[checkPos + bestLength] != data[pos + bestLength]) {
                    continue;
                }
            }
        }

        int length = 0;
        while (length < maxLength &&
               pos + length < data.size() &&
               data[checkPos + length] == data[pos + length]) {
            length++;
        }

        // Update only if strictly longer (keeps first equal match = highest offset)
        if (length > bestLength && length >= 2) {
            bestLength = length;
            bestOffset = offset;

            // Early termination
            if (bestLength >= maxLength) {
                break;
            }
        }
    }

    // Long matches require offset >= 1 for valid encoding
    if (bestOffset > 0 && bestLength >= 2) {
        bool isShortMatch = (bestLength >= 2 && bestLength <= 5 && bestOffset <= 256);
        if (!isShortMatch) {
            if (bestOffset < 1) {
                return {0, 0};
            }
        }
    }

    return {bestLength, bestOffset};
}

int LZSS::calculateMatchCost(int length, int offset)
{
    if (length >= 2 && length <= 5 && offset <= 256) {
        // Short match: 1 flag + 1 type + 2 length + 8 offset = 12 bits
        return 12;
    } else if (length < 10) {
        // Long match: 1 flag + 1 type + 16 data = 18 bits
        return 18;
    } else {
        // Very long match with continuation bytes
        int extraBytes = (length - 9 + 254) / 255;
        return 18 + (extraBytes * 8);
    }
}

int LZSS::findOptimalMatchLength(const QByteArray& data, int pos, int matchLength, int matchOffset)
{
    if (matchLength < 50 || matchLength > 500) {
        return matchLength;
    }

    int bestTruncateAt = matchLength;
    int bestSavings = 0;
    int currentCost = calculateMatchCost(matchLength, matchOffset);

    for (int checkOffset = 10; checkOffset < matchLength - 10; checkOffset += 10) {
        int futurePos = pos + checkOffset;
        if (futurePos >= data.size()) {
            break;
        }

        auto [futureLength, futureOffset] = findBestMatch(data, futurePos);

        if (futureLength < 50) {
            continue;
        }

        int truncatedCost = calculateMatchCost(checkOffset, matchOffset);
        int futureCost = calculateMatchCost(futureLength, futureOffset);
        int remainingAfterFull = matchLength - checkOffset;
        int remainingCostGuess = calculateMatchCost(remainingAfterFull, matchOffset);

        int strategyTruncate = truncatedCost + futureCost;
        int strategyFull = currentCost + remainingCostGuess;

        int savings = strategyFull - strategyTruncate;
        if (savings > bestSavings && savings >= 10) {
            bestSavings = savings;
            bestTruncateAt = checkOffset;
        }
    }

    return bestTruncateAt;
}

std::tuple<bool, int, int> LZSS::peekNextDecision(const QByteArray& data, int pos, int currLength)
{
    int nextPos = pos + currLength;
    if (nextPos >= data.size()) {
        return {false, 0, 0};
    }

    auto [nextLength, nextOffset] = findBestMatch(data, nextPos);

    // Apply same lazy matching logic as main loop would
    if (nextLength >= 2 && nextPos + 1 < data.size()) {
        auto [lookaheadLength, lookaheadOffset] = findBestMatch(data, nextPos + 1);

        bool nextIsShort = (nextLength >= 2 && nextLength <= 5 && nextOffset <= 256);
        bool lookaheadIsShort = (lookaheadLength >= 2 && lookaheadLength <= 5 && lookaheadOffset <= 256);

        int adjustment = nextIsShort ? 2 : 1;

        if (nextIsShort && !lookaheadIsShort && lookaheadLength >= 2) {
            adjustment += 2;
        }
        if (lookaheadIsShort && !nextIsShort) {
            adjustment -= 1;
        }
        if (adjustment < 1) {
            adjustment = 1;
        }
        if (nextIsShort && lookaheadIsShort) {
            adjustment = 1;
        }

        if (lookaheadLength >= nextLength + adjustment) {
            nextLength = 0;
        }
    }

    if (nextLength >= 2) {
        int matchCost = calculateMatchCost(nextLength, nextOffset);
        int literalCost = 9 * nextLength;
        if (matchCost >= literalCost) {
            nextLength = 0;
        }
    }

    bool isMatch = (nextLength >= 2);
    return {isMatch, nextLength, nextOffset};
}

QByteArray LZSS::compress(const QByteArray& data)
{
    if (data.isEmpty()) {
        return QByteArray();
    }

    // Add 2-byte zero prefix
    QByteArray bufferedData;
    bufferedData.append(static_cast<char>(0));
    bufferedData.append(static_cast<char>(0));
    bufferedData.append(data);

    CompressState state;

    // Start at position 2 (after 2-byte prefix)
    int pos = 2;

    while (pos < bufferedData.size()) {
        // Find best match at current position
        auto [currLength, currOffset] = findBestMatch(bufferedData, pos);

        // Force literal at the very first position (game behavior)
        if (pos == 2) {
            currLength = 0;
        }

        // LAZY MATCHING with exact game logic
        if (currLength >= 2 && pos + 1 < bufferedData.size()) {
            auto [nextLength, nextOffset] = findBestMatch(bufferedData, pos + 1);

            bool currIsShort = (currLength >= 2 && currLength <= 5 && currOffset <= 256);
            bool nextIsShort = (nextLength >= 2 && nextLength <= 5 && nextOffset <= 256);

            int adjustment = currIsShort ? 2 : 1;

            if (currIsShort && !nextIsShort && nextLength >= 2) {
                adjustment += 2;
            }
            if (nextIsShort && !currIsShort) {
                adjustment -= 1;
            }
            if (adjustment < 1) {
                adjustment = 1;
            }
            if (currIsShort && nextIsShort) {
                adjustment = 1;
            }

            if (nextLength >= currLength + adjustment) {
                currLength = 0;  // Force literal
            }
        }

        if (currLength >= 2) {
            // Check if match is worth encoding
            int matchCost = calculateMatchCost(currLength, currOffset);
            int literalCost = 9 * currLength;

            if (matchCost >= literalCost) {
                currLength = 0;
            }
        }

        if (currLength >= 2) {
            // Optimize long matches
            currLength = findOptimalMatchLength(bufferedData, pos, currLength, currOffset);
        }

        // SCENARIO 1: Match-Follow-Match Optimization
        bool scenario1Applied = false;
        if (currLength == 3 && state.prevWasMatch && state.prevTokenPos >= 0) {
            if ((static_cast<uint8_t>(state.output[state.prevTokenPos]) & 0x03) == 0) {
                auto [nextIsMatch, unused1, unused2] = peekNextDecision(bufferedData, pos, currLength);
                if (nextIsMatch) {
                    scenario1Applied = true;

                    // Encode all 3 bytes as literals
                    for (int i = 0; i < 3; ++i) {
                        uint8_t byteVal = static_cast<uint8_t>(bufferedData[pos + i]);
                        addBit(state, 0);
                        state.output.append(static_cast<char>(byteVal));
                    }

                    state.prevWasMatch = false;
                    pos += 3;
                    continue;
                }
            }
        }

        if (currLength >= 2) {
            // Encode match
            addBit(state, 1);

            if (currLength >= 2 && currLength <= 5 && currOffset <= 256) {
                // Short match
                addBit(state, 0);

                int lenBits = currLength - 2;
                for (int i = 0; i < 2; ++i) {
                    addBit(state, (lenBits >> i) & 1);
                }

                // Track token position for Scenario 1
                state.prevTokenPos = state.output.size();
                state.output.append(static_cast<char>((currOffset - 1) & 0xFF));
                state.prevWasMatch = true;
            } else {
                // Long match
                addBit(state, 1);

                // Track token position for Scenario 1
                state.prevTokenPos = state.output.size();

                if (currLength < 10) {
                    uint8_t byte1 = ((currLength - 2) << 5) | (currOffset & 0x1F);
                    uint8_t byte2 = (currOffset >> 5) & 0xFF;
                    state.output.append(static_cast<char>(byte1));
                    state.output.append(static_cast<char>(byte2));
                } else {
                    uint8_t byte1 = currOffset & 0x1F;
                    uint8_t byte2 = (currOffset >> 5) & 0xFF;
                    state.output.append(static_cast<char>(byte1));
                    state.output.append(static_cast<char>(byte2));

                    int remaining = currLength - 9;
                    while (remaining >= 0xFF) {
                        state.output.append(static_cast<char>(0));
                        remaining -= 0xFF;
                    }
                    state.output.append(static_cast<char>(remaining & 0xFF));
                }
                state.prevWasMatch = true;
            }

            pos += currLength;
        } else {
            // Encode literal
            uint8_t byteVal = static_cast<uint8_t>(bufferedData[pos]);
            addBit(state, 0);
            state.output.append(static_cast<char>(byteVal));

            state.prevWasMatch = false;
            pos += 1;
        }
    }

    // Terminator
    addBit(state, 1);
    addBit(state, 1);
    state.output.append(static_cast<char>(0x20));
    state.output.append(static_cast<char>(0x00));

    // Flush final bits
    if (state.bitCounter > 0) {
        state.output[state.flagBytePtr] = static_cast<char>(((1 << state.bitCounter) - 1) & state.bitAccum);
    }

    return state.output;
}

QByteArray LZSS::decompress(const QByteArray& compressed)
{
    if (compressed.isEmpty()) {
        return QByteArray();
    }

    QByteArray output;
    int inPtr = 0;
    int flags = 0;
    int flagBits = 0;

    while (inPtr < compressed.size()) {
        // Read flag bit
        if (flagBits < 1) {
            if (inPtr >= compressed.size()) break;
            flags = static_cast<uint8_t>(compressed[inPtr]);
            inPtr++;
            flagBits = 8;
        }

        int flagBit = flags & 1;
        flags >>= 1;
        flagBits--;

        if (flagBit == 0) {
            // Literal byte
            if (inPtr >= compressed.size()) break;
            output.append(compressed[inPtr]);
            inPtr++;
        } else {
            // Match - read second flag bit
            if (flagBits < 1) {
                if (inPtr >= compressed.size()) break;
                flags = static_cast<uint8_t>(compressed[inPtr]);
                inPtr++;
                flagBits = 8;
            }

            int flagBit2 = flags & 1;
            flags >>= 1;
            flagBits--;

            if (flagBit2 == 0) {
                // Short match (length 2-5, offset 1-256)
                if (flagBits < 2) {
                    if (inPtr >= compressed.size()) break;
                    flags |= static_cast<uint8_t>(compressed[inPtr]) << flagBits;
                    inPtr++;
                    flagBits += 8;
                }

                int length = (flags & 3) + 2;
                flags >>= 2;
                flagBits -= 2;

                if (inPtr >= compressed.size()) break;
                int offsetByte = static_cast<uint8_t>(compressed[inPtr]);
                inPtr++;

                int distance = offsetByte + 1;
                int srcPos = output.size() - distance;

                for (int i = 0; i < length; ++i) {
                    if (srcPos < 0) {
                        output.append(static_cast<char>(0));
                    } else {
                        output.append(output[srcPos]);
                    }
                    srcPos++;
                }
            } else {
                // Long match (length 3+, offset 0-8191)
                if (inPtr + 1 >= compressed.size()) break;

                int byte1 = static_cast<uint8_t>(compressed[inPtr]);
                int byte2 = static_cast<uint8_t>(compressed[inPtr + 1]);
                inPtr += 2;

                int lenField = byte1 >> 5;
                int lowOffset = byte1 & 0x1F;
                int highOffset = byte2;
                int distance = (highOffset << 5) | lowOffset;

                // Terminator check
                if (distance == 0) break;

                int length;
                if (lenField == 0) {
                    // Variable length encoding
                    length = 9;
                    while (inPtr < compressed.size() && static_cast<uint8_t>(compressed[inPtr]) == 0) {
                        inPtr++;
                        length += 255;
                    }
                    if (inPtr >= compressed.size()) break;
                    length += static_cast<uint8_t>(compressed[inPtr]);
                    inPtr++;
                } else {
                    length = lenField + 2;
                }

                int srcPos = output.size() - distance;

                for (int i = 0; i < length; ++i) {
                    if (srcPos < 0) {
                        output.append(static_cast<char>(0));
                    } else {
                        output.append(output[srcPos]);
                    }
                    srcPos++;
                }
            }
        }
    }

    return output;
}

} // namespace acb
