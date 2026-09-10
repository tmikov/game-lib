cmake_minimum_required(VERSION 3.21)
project(gamelib_compile_includes LANGUAGES C CXX)
add_subdirectory("${GAMELIB_ROOT}" gamelib EXCLUDE_FROM_ALL)

add_library(inc_entt STATIC entt.cc)
target_link_libraries(inc_entt PRIVATE gamelib::entt)

add_library(inc_itlib STATIC itlib.cc)
target_link_libraries(inc_itlib PRIVATE gamelib::itlib)

add_library(inc_handmademath STATIC handmademath.c)
target_link_libraries(inc_handmademath PRIVATE gamelib::handmademath)

add_library(inc_box2d STATIC box2d.c)
target_link_libraries(inc_box2d PRIVATE gamelib::box2d)

add_library(inc_stbvorbis STATIC stbvorbis.c)
target_link_libraries(inc_stbvorbis PRIVATE gamelib::stb_vorbis)
