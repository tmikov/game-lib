cmake_minimum_required(VERSION 3.21)
project(gamelib_option_off LANGUAGES C)
set(GAMELIB_MINIAUDIO OFF)     # a normal variable; CMP0077 makes option() honour it
add_subdirectory("${GAMELIB_ROOT}" gamelib EXCLUDE_FROM_ALL)
if(TARGET gamelib_miniaudio)
  message(FATAL_ERROR "GAMELIB_MINIAUDIO=OFF but gamelib_miniaudio was declared")
endif()
