#include <QCoreApplication>
#include <QFile>
#include <QDebug>
#include "model/OptionsFile.h"
#include "model/Section.h"

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    QString filePath = "/mnt/f/ClaudeHole/acbserializer/OPTIONS.PC";
    if (argc > 1) {
        filePath = argv[1];
    }

    qDebug() << "Loading:" << filePath;

    // Check file exists and is readable
    QFile testFile(filePath);
    if (!testFile.exists()) {
        qCritical() << "File does not exist:" << filePath;
        return 1;
    }
    if (!testFile.open(QIODevice::ReadOnly)) {
        qCritical() << "Cannot open file:" << filePath;
        return 1;
    }
    qint64 fileSize = testFile.size();
    testFile.close();
    qDebug() << "File size:" << fileSize << "bytes";

    qDebug() << "Creating OptionsFile...";
    acb::OptionsFile file;
    qDebug() << "Calling load()...";
    if (!file.load(filePath)) {
        qCritical() << "Failed to load file";
        return 1;
    }
    qDebug() << "Load succeeded";

    qDebug() << "Platform:" << (file.platform() == acb::Platform::PC ? "PC" : "PS3");
    qDebug() << "Section count:" << file.sectionCount();

    for (int i = 0; i < file.sectionCount(); ++i) {
        acb::Section* section = file.section(i);
        if (section) {
            qDebug() << "  Section" << i << ":" << section->sectionName()
                     << "- valid:" << section->isValid()
                     << "- decompressed size:" << section->rawDecompressed().size();
        }
    }

    // Test round-trip: serialize and compare
    QByteArray original;
    {
        QFile f(filePath);
        if (f.open(QIODevice::ReadOnly)) {
            original = f.readAll();
        }
    }

    QByteArray serialized = file.serialize();

    if (original == serialized) {
        qDebug() << "Round-trip: PASS (identical)";
    } else {
        qDebug() << "Round-trip: FAIL";
        qDebug() << "  Original size:" << original.size();
        qDebug() << "  Serialized size:" << serialized.size();

        // Save serialized for comparison
        QFile outFile("/tmp/serialized.bin");
        if (outFile.open(QIODevice::WriteOnly)) {
            outFile.write(serialized);
            outFile.close();
            qDebug() << "  Saved serialized to /tmp/serialized.bin";
        }

        // Find first difference
        int diffPos = -1;
        for (int i = 0; i < qMin(original.size(), serialized.size()); ++i) {
            if (original[i] != serialized[i]) {
                diffPos = i;
                break;
            }
        }
        if (diffPos >= 0) {
            qDebug() << "  First difference at offset:" << Qt::hex << diffPos;

            // Show context around difference
            int start = qMax(0, diffPos - 8);
            int end = qMin(qMin(original.size(), serialized.size()), diffPos + 24);

            QString origHex, serHex;
            for (int i = start; i < end; ++i) {
                origHex += QString("%1 ").arg((unsigned char)original[i], 2, 16, QChar('0'));
                serHex += QString("%1 ").arg((unsigned char)serialized[i], 2, 16, QChar('0'));
            }
            qDebug().noquote() << "  Original:  " << origHex;
            qDebug().noquote() << "  Serialized:" << serHex;
        }
        return 1;
    }

    return 0;
}
