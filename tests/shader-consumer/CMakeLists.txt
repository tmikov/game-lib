cmake_minimum_required(VERSION 3.21)
project(gamelib_shader_consumer LANGUAGES C)

# The point of this project: call gamelib_add_shader() from a directory scope
# that is NOT inside game-lib's own tree -- game-lib is a *subdirectory* of
# this project, not the other way around, exactly as a real consumer's
# top-level CMakeLists.txt would be. Every in-tree example calls
# gamelib_add_shader() from inside game-lib's own directory tree, which is
# precisely the scope where a directory-scoped set() bug in
# cmake/GameLibShader.cmake stays invisible.
add_subdirectory("${GAMELIB_ROOT}" gamelib EXCLUDE_FROM_ALL)

add_executable(shader_consumer main.c)
target_link_libraries(shader_consumer PRIVATE gamelib::sokol_gfx gamelib::sokol_log)
gamelib_add_shader(TARGET shader_consumer INPUT triangle.glsl OUTPUT triangle.h)
