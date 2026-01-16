# Core library - binary format handling (minimal Qt dependencies)
add_library(acb_core STATIC
    core/BinaryReader.cpp
    core/BinaryWriter.cpp
    core/Checksum.cpp
    core/LZSS.cpp
    core/HashLookup.cpp
)
target_include_directories(acb_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(acb_core PUBLIC Qt6::Core)

# Model library - data structures
add_library(acb_model STATIC
    model/PropertyValue.cpp
    model/Property.cpp
    model/SectionHeader.cpp
    model/Section.cpp
    model/Section1.cpp
    model/Section2.cpp
    model/Section3.cpp
    model/Section4.cpp
    model/UnknownSection.cpp
    model/OptionsFile.cpp
)
target_include_directories(acb_model PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(acb_model PUBLIC acb_core Qt6::Core)

# ViewModel library - Qt models for QML
add_library(acb_viewmodel STATIC
    viewmodel/PropertyTreeItem.cpp
    viewmodel/PropertyTreeModel.cpp
    viewmodel/SectionListModel.cpp
    viewmodel/OptionsFileModel.cpp
    viewmodel/UndoCommands.cpp
)
target_include_directories(acb_viewmodel PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(acb_viewmodel PUBLIC acb_model Qt6::Core Qt6::Gui)

# Utility library
add_library(acb_util STATIC
    util/JsonExporter.cpp
)
target_include_directories(acb_util PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(acb_util PUBLIC acb_model Qt6::Core)
