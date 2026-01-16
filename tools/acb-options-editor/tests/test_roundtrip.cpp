#include <QtTest>
#include <QFile>
#include "model/OptionsFile.h"
#include "core/LZSS.h"
#include "core/Checksum.h"

using namespace acb;

class TestRoundtrip : public QObject {
    Q_OBJECT

private slots:
    void testPlatformDetectionPC()
    {
        // Create minimal PC-like data with magic pattern at 0x10
        QByteArray data(0x30, 0);
        // Magic pattern at offset 0x10
        data[0x10] = 0x33;
        data[0x11] = 0xAA;
        data[0x12] = 0xFB;
        data[0x13] = 0x57;

        Platform platform = OptionsFile::detectPlatform(data);
        QCOMPARE(platform, Platform::PC);
    }

    void testPlatformDetectionPS3Size()
    {
        // PS3 files are exactly 51200 bytes
        QByteArray data(51200, 0);
        // Add magic at PS3 offset (0x18 = 8-byte prefix + 0x10)
        data[0x18] = 0x33;
        data[0x19] = 0xAA;
        data[0x1A] = 0xFB;
        data[0x1B] = 0x57;

        Platform platform = OptionsFile::detectPlatform(data);
        // Should detect PS3 based on magic pattern location
        QCOMPARE(platform, Platform::PS3);
    }

    void testLZSSRoundTrip()
    {
        // Test that LZSS compression/decompression is lossless
        QByteArray original;
        for (int i = 0; i < 1000; ++i) {
            original.append("TestPattern");
            original.append(static_cast<char>(i & 0xFF));
        }

        QByteArray compressed = LZSS::compress(original);
        QByteArray decompressed = LZSS::decompress(compressed);

        QCOMPARE(decompressed, original);
    }

    void testSectionHeaderBuild()
    {
        // Test that we can build and serialize section headers
        SectionHeader header;
        header.build(0x11FACE11, 100, 50, 0x12345678, Platform::PC);

        QCOMPARE(header.sectionId(), 0x11FACE11u);
        QCOMPARE(header.uncompressedSize(), 100);
        QCOMPARE(header.compressedSize(), 50);
        QCOMPARE(header.checksum(), 0x12345678u);
        QVERIFY(header.isValid());
    }

    // Test with actual OPTIONS files if available
    void testRoundTripPCFile()
    {
        QString testFile = "../OPTIONS.PC";
        if (!QFile::exists(testFile)) {
            QSKIP("OPTIONS.PC not found - skipping file-based test");
        }

        QFile file(testFile);
        QVERIFY(file.open(QIODevice::ReadOnly));
        QByteArray originalData = file.readAll();
        file.close();

        OptionsFile options;
        QVERIFY(options.load(testFile));
        QCOMPARE(options.platform(), Platform::PC);
        QVERIFY(options.sectionCount() >= 3);

        // Serialize back
        QByteArray serializedData = options.serialize();

        // Should match original exactly if no edits
        QCOMPARE(serializedData, originalData);
    }

    void testRoundTripPS3File()
    {
        QString testFile = "../OPTIONS.PS3";
        if (!QFile::exists(testFile)) {
            QSKIP("OPTIONS.PS3 not found - skipping file-based test");
        }

        QFile file(testFile);
        QVERIFY(file.open(QIODevice::ReadOnly));
        QByteArray originalData = file.readAll();
        file.close();

        OptionsFile options;
        QVERIFY(options.load(testFile));
        QCOMPARE(options.platform(), Platform::PS3);
        QVERIFY(options.sectionCount() >= 3);

        // Serialize back
        QByteArray serializedData = options.serialize();

        // Should match original exactly if no edits
        QCOMPARE(serializedData, originalData);
    }
};

QTEST_MAIN(TestRoundtrip)
#include "test_roundtrip.moc"
