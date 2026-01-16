#include <QtTest>
#include "core/LZSS.h"

using namespace acb;

class TestLZSS : public QObject {
    Q_OBJECT

private slots:
    void testDecompressEmpty()
    {
        QByteArray compressed;
        QByteArray result = LZSS::decompress(compressed);
        QVERIFY(result.isEmpty());
    }

    void testCompressEmpty()
    {
        QByteArray data;
        QByteArray result = LZSS::compress(data);
        QVERIFY(result.isEmpty());
    }

    void testRoundTripSimple()
    {
        QByteArray original = "Hello, World!";
        QByteArray compressed = LZSS::compress(original);
        QByteArray decompressed = LZSS::decompress(compressed);
        QCOMPARE(decompressed, original);
    }

    void testRoundTripRepeating()
    {
        // Data with repeating patterns should compress well
        QByteArray original;
        for (int i = 0; i < 100; ++i) {
            original.append("ABCD");
        }
        QByteArray compressed = LZSS::compress(original);
        QByteArray decompressed = LZSS::decompress(compressed);
        QCOMPARE(decompressed, original);
        QVERIFY(compressed.size() < original.size());
    }

    void testRoundTripBinary()
    {
        // Binary data with all byte values
        QByteArray original;
        for (int i = 0; i < 256; ++i) {
            original.append(static_cast<char>(i));
        }
        QByteArray compressed = LZSS::compress(original);
        QByteArray decompressed = LZSS::decompress(compressed);
        QCOMPARE(decompressed, original);
    }

    void testRoundTripLarge()
    {
        // Large data with mixed patterns
        QByteArray original;
        for (int i = 0; i < 10000; ++i) {
            original.append(static_cast<char>(i % 256));
            if (i % 100 == 0) {
                original.append("MARKER");
            }
        }
        QByteArray compressed = LZSS::compress(original);
        QByteArray decompressed = LZSS::decompress(compressed);
        QCOMPARE(decompressed, original);
    }
};

QTEST_MAIN(TestLZSS)
#include "test_lzss.moc"
