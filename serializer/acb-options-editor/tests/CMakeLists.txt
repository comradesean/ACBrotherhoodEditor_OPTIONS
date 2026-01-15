# Tests
find_package(Qt6 REQUIRED COMPONENTS Test)

# LZSS tests
add_executable(test_lzss test_lzss.cpp)
target_link_libraries(test_lzss PRIVATE acb_core Qt6::Test)
add_test(NAME test_lzss COMMAND test_lzss)

# Checksum tests
add_executable(test_checksum test_checksum.cpp)
target_link_libraries(test_checksum PRIVATE acb_core Qt6::Test)
add_test(NAME test_checksum COMMAND test_checksum)

# Round-trip tests
add_executable(test_roundtrip test_roundtrip.cpp)
target_link_libraries(test_roundtrip PRIVATE acb_model acb_util Qt6::Test)
add_test(NAME test_roundtrip COMMAND test_roundtrip)

# File loading test (manual test, not added to ctest)
add_executable(test_load_file test_load_file.cpp)
target_link_libraries(test_load_file PRIVATE acb_model acb_util Qt6::Core)
