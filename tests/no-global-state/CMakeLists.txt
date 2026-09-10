cmake_minimum_required(VERSION 3.21)
project(gamelib_no_global_state LANGUAGES C CXX)

# Capture the parent's state, add game-lib, then assert nothing changed. A
# directory-scoped set() inside game-lib is invisible here by construction --
# that is what the trace half of this test is for.
set(_before_cxx "${CMAKE_CXX_STANDARD}")
set(_before_c   "${CMAKE_C_STANDARD}")
set(_before_sfx "${CMAKE_EXECUTABLE_SUFFIX}")
get_directory_property(_before_inc INCLUDE_DIRECTORIES)

# Snapshot the whole cache too: a directory-scoped set() is invisible to us,
# but a CACHE write is not, and criterion 8 bans those just the same. Record
# names *and* values now, before add_subdirectory, so a changed value is
# caught and not just a removed name.
get_cmake_property(_before_cache_vars CACHE_VARIABLES)
foreach(_name IN LISTS _before_cache_vars)
  get_property(_v CACHE ${_name} PROPERTY VALUE)
  set(_gamelib_cache_before_${_name} "${_v}")
endforeach()

add_subdirectory("${GAMELIB_ROOT}" gamelib EXCLUDE_FROM_ALL)

foreach(pair "CXX_STANDARD;${_before_cxx};${CMAKE_CXX_STANDARD}"
             "C_STANDARD;${_before_c};${CMAKE_C_STANDARD}"
             "EXECUTABLE_SUFFIX;${_before_sfx};${CMAKE_EXECUTABLE_SUFFIX}")
  list(GET pair 0 _what)
  list(GET pair 1 _was)
  list(GET pair 2 _now)
  if(NOT "${_was}" STREQUAL "${_now}")
    message(FATAL_ERROR "game-lib changed CMAKE_${_what}: '${_was}' -> '${_now}'")
  endif()
endforeach()

get_directory_property(_after_inc INCLUDE_DIRECTORIES)
if(NOT "${_before_inc}" STREQUAL "${_after_inc}")
  message(FATAL_ERROR "game-lib changed the parent's INCLUDE_DIRECTORIES")
endif()

# (1) No pre-existing cache entry may have changed value.
foreach(_name IN LISTS _before_cache_vars)
  get_property(_v CACHE ${_name} PROPERTY VALUE)
  if(NOT "${_v}" STREQUAL "${_gamelib_cache_before_${_name}}")
    message(FATAL_ERROR
      "game-lib changed cache entry '${_name}': "
      "'${_gamelib_cache_before_${_name}}' -> '${_v}'")
  endif()
endforeach()

# (2) Every newly created entry must be explained. Allowed: game-lib's own
# GAMELIB_* options; the three entries a nested project() writes (verified
# empirically -- a nested project() call creates exactly these three STATIC
# cache entries); and, if this project ever needs one, an entry created by
# one of CMake's own discovery modules (find_package, enable_language, ...).
# That last category is intentionally empty: run against this test project,
# game-lib creates no such entry, so nothing is whitelisted for it. If one
# ever appears, this must fail rather than silently pass -- add it here only
# after confirming by hand that CMake's own machinery, not game-lib's code,
# created it, with a comment saying what did.
set(_gamelib_allowed_new_cache
  game-lib_SOURCE_DIR
  game-lib_BINARY_DIR
  game-lib_IS_TOP_LEVEL
)
get_cmake_property(_after_cache_vars CACHE_VARIABLES)
foreach(_name IN LISTS _after_cache_vars)
  if(NOT _name IN_LIST _before_cache_vars
     AND NOT _name MATCHES "^GAMELIB_"
     AND NOT _name IN_LIST _gamelib_allowed_new_cache)
    message(FATAL_ERROR "game-lib created unexplained cache entry '${_name}'")
  endif()
endforeach()

# Every target game-lib declared must be namespaced. Walk BUILDSYSTEM_TARGETS
# over game-lib's directory tree rather than parsing `--target help`, which also
# lists CMake's own built-ins (all, clean, edit_cache, ...) and would flag them.
function(gamelib_assert_namespaced dir)
  get_property(_tgts DIRECTORY "${dir}" PROPERTY BUILDSYSTEM_TARGETS)
  foreach(t IN LISTS _tgts)
    if(NOT t MATCHES "^gamelib_")
      message(FATAL_ERROR "game-lib declared un-namespaced target '${t}' in ${dir}")
    endif()
  endforeach()
  get_property(_subs DIRECTORY "${dir}" PROPERTY SUBDIRECTORIES)
  foreach(d IN LISTS _subs)
    gamelib_assert_namespaced("${d}")
  endforeach()
endfunction()
gamelib_assert_namespaced("${GAMELIB_ROOT}")
