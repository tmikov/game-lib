# Upstream's own .cpp files, compiled from the vendored subtree. They include
# their headers sibling-relative ("imgui.h"), which resolves without any PRIVATE
# include directory because the files sit together.
gamelib_add_library(NAME imgui
  SOURCES
    imgui/imgui.cpp
    imgui/imgui_draw.cpp
    imgui/imgui_tables.cpp
    imgui/imgui_widgets.cpp
    imgui/imgui_demo.cpp)     # ShowDemoWindow() is genuinely used; compile-time cost only
target_compile_features(gamelib_imgui PUBLIC cxx_std_11)
