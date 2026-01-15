cmake_minimum_required(VERSION 3.16)
project(acb-options-editor VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# Find Qt packages
find_package(Qt6 REQUIRED COMPONENTS
    Core
    Gui
    Quick
    QuickControls2
    Widgets
)

qt_standard_project_setup()

# Add source libraries
add_subdirectory(src)

# Add third-party libraries
add_subdirectory(third_party)

# Main executable
qt_add_executable(acb-options-editor
    main.cpp
)

# QML module
qt_add_qml_module(acb-options-editor
    URI AcbOptionsEditor
    VERSION 1.0
    QML_FILES
        qml/main.qml
        qml/components/MenuBar.qml
        qml/components/SectionTabs.qml
        qml/components/PropertyTreeView.qml
        qml/components/HexEditor.qml
        qml/components/PropertyEditor.qml
        qml/components/StatusBar.qml
        qml/dialogs/ExportDialog.qml
)

target_link_libraries(acb-options-editor PRIVATE
    acb_core
    acb_model
    acb_viewmodel
    acb_util
    Qt6::Core
    Qt6::Gui
    Qt6::Quick
    Qt6::QuickControls2
    Qt6::Widgets
)

# Tests
option(BUILD_TESTING "Build tests" ON)
if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(tests)
endif()
