cmake_minimum_required(VERSION 3.21)

# LANGUAGES C only: project(... C CXX) would force every consumer through C++
# compiler detection, including one selecting only C libraries, and
# EXCLUDE_FROM_ALL cannot suppress that. CXX is enabled below, on demand.
project(game-lib LANGUAGES C)

set(GAMELIB_CMAKE_DIR "${CMAKE_CURRENT_LIST_DIR}/cmake")
include("${GAMELIB_CMAKE_DIR}/GameLibLibrary.cmake")

option(GAMELIB_SOKOL        "Build sokol targets"        ON)
option(GAMELIB_IMGUI        "Build Dear ImGui targets"   ON)
option(GAMELIB_MINIAUDIO    "Build miniaudio target"     ON)
option(GAMELIB_STB          "Build stb targets"          ON)
option(GAMELIB_BOX2D        "Build Box2D target"         ON)
option(GAMELIB_ENTT         "Build EnTT target"          ON)
option(GAMELIB_HANDMADEMATH "Build HandmadeMath target"  ON)
option(GAMELIB_ITLIB        "Build itlib target"         ON)

# Enabled here, at the common ancestor of libs/ and examples/. CMake requires a
# language to be enabled in the highest directory common to every target using
# it, including through link dependencies.
if(GAMELIB_IMGUI OR GAMELIB_ENTT OR GAMELIB_ITLIB)
  enable_language(CXX)
endif()

add_subdirectory(libs)

include("${GAMELIB_CMAKE_DIR}/GameLibShader.cmake")

if(PROJECT_IS_TOP_LEVEL)
  add_subdirectory(examples)
endif()

get_property(_gamelib_declared GLOBAL PROPERTY GAMELIB_DECLARED_TARGETS)
list(JOIN _gamelib_declared " " _gamelib_declared_str)
message(STATUS "game-lib targets: ${_gamelib_declared_str}")
