#include <QtTest>
#include "core/Checksum.h"

using namespace acb;

class TestChecksum : public QObject {
    Q_OBJECT

private slots:
    void testAdler32Empty()
    {
        QByteArray data;
        uint32_t result = Checksum::adler32ZeroSeed(data);
        // With zero seed, empty data should give 0
        QCOMPARE(result, 0u);
    }

    void testAdler32Simple()
    {
        QByteArray data = "Hello";
        uint32_t result = Checksum::adler32ZeroSeed(data);
        // Verify it produces a non-zero result
        QVERIFY(result != 0);
    }

    void testAdler32Consistency()
    {
        QByteArray data = "Test data for checksum";
        uint32_t result1 = Checksum::adler32ZeroSeed(data);
        uint32_t result2 = Checksum::adler32ZeroSeed(data);
        QCOMPARE(result1, result2);
    }

    void testCrc32PS3Empty()
    {
        QByteArray data;
        uint32_t result = Checksum::crc32PS3(data);
        // Empty data with PS3 parameters
        QVERIFY(result != 0);  // CRC has XOR out
    }

    void testCrc32PS3Simple()
    {
        QByteArray data = "Hello";
        uint32_t result = Checksum::crc32PS3(data);
        QVERIFY(result != 0);
    }

    void testCrc32PS3Consistency()
    {
        QByteArray data = "Test data for CRC32";
        uint32_t result1 = Checksum::crc32PS3(data);
        uint32_t result2 = Checksum::crc32PS3(data);
        QCOMPARE(result1, result2);
    }

    void testDifferentDataDifferentChecksum()
    {
        QByteArray data1 = "Data A";
        QByteArray data2 = "Data B";

        uint32_t adler1 = Checksum::adler32ZeroSeed(data1);
        uint32_t adler2 = Checksum::adler32ZeroSeed(data2);
        QVERIFY(adler1 != adler2);

        uint32_t crc1 = Checksum::crc32PS3(data1);
        uint32_t crc2 = Checksum::crc32PS3(data2);
        QVERIFY(crc1 != crc2);
    }
};

QTEST_MAIN(TestChecksum)
#include "test_checksum.moc"
