#pragma once

#include "Section.h"

namespace acb {

// UnknownSection stores decompressed data as a hex blob
// Used when we don't recognize the root hash
class UnknownSection : public Section {
public:
    UnknownSection();
    ~UnknownSection() override;

    bool parse() override;
    QByteArray serialize() const override;

    QString sectionName() const override;
    int sectionNumber() const override { return 0; }
    bool isKnown() const override { return false; }
};

} // namespace acb
