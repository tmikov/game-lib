# Locate sokol-shdc by HOST, not target: the tool runs on the build machine even
# when cross-compiling to Emscripten, which is the common case.
#
# CACHE INTERNAL, not a plain set(): this file is include()d once, from
# game-lib's own root directory scope, but gamelib_add_shader() is a global
# function callable from any consumer's directory scope. A plain set() here
# would be invisible there -- CMake variables propagate only downward through
# add_subdirectory, and a consumer's CMakeLists.txt is never a descendant of
# game-lib's. A CACHE entry has no directory scope, so it reads back correctly
# no matter where gamelib_add_shader() is called from. Both entries are
# GAMELIB_-prefixed, so §3.3's cache whitelist (criterion 8b) already accepts
# them unchanged.
if(GAMELIB_SOKOL_SHDC)
  set(GAMELIB_SHDC "${GAMELIB_SOKOL_SHDC}" CACHE INTERNAL "sokol-shdc binary path")
else()
  set(_bin "${CMAKE_CURRENT_LIST_DIR}/../tools/sokol-shdc/bin")
  if(CMAKE_HOST_SYSTEM_NAME STREQUAL "Linux")
    if(CMAKE_HOST_SYSTEM_PROCESSOR MATCHES "aarch64|arm64")
      set(GAMELIB_SHDC "${_bin}/linux_arm64/sokol-shdc" CACHE INTERNAL "sokol-shdc binary path")
    else()
      set(GAMELIB_SHDC "${_bin}/linux/sokol-shdc" CACHE INTERNAL "sokol-shdc binary path")
    endif()
  elseif(CMAKE_HOST_SYSTEM_NAME STREQUAL "Darwin")
    if(CMAKE_HOST_SYSTEM_PROCESSOR MATCHES "arm64")
      set(GAMELIB_SHDC "${_bin}/osx_arm64/sokol-shdc" CACHE INTERNAL "sokol-shdc binary path")
    else()
      set(GAMELIB_SHDC "${_bin}/osx/sokol-shdc" CACHE INTERNAL "sokol-shdc binary path")
    endif()
  elseif(CMAKE_HOST_SYSTEM_NAME STREQUAL "Windows")
    set(GAMELIB_SHDC "${_bin}/win32/sokol-shdc.exe" CACHE INTERNAL "sokol-shdc binary path")
  else()
    set(GAMELIB_SHDC "GAMELIB_SHDC-NOTFOUND" CACHE INTERNAL "sokol-shdc binary path")
  endif()
endif()

# Default --slang from the selected backend, following upstream's own documented
# mapping. Left empty under the dummy backend: there is no valid shader language,
# and gamelib_add_shader() below turns that into a clear configure error. Also
# CACHE INTERNAL, for the same cross-directory-scope reason as GAMELIB_SHDC above.
set(_slang_map glcore glsl410 gles3 glsl300es metal metal_macos d3d11 hlsl5)
list(FIND _slang_map "${GAMELIB_SOKOL_BACKEND_RESOLVED}" _si)
if(_si EQUAL -1)
  set(GAMELIB_SHDC_SLANG "" CACHE INTERNAL "default --slang for the resolved sokol backend")
else()
  math(EXPR _si "${_si} + 1")
  list(GET _slang_map ${_si} _slang)
  set(GAMELIB_SHDC_SLANG "${_slang}" CACHE INTERNAL "default --slang for the resolved sokol backend")
endif()

function(gamelib_add_shader)
  cmake_parse_arguments(PARSE_ARGV 0 ARG "" "TARGET;INPUT;OUTPUT;SLANG" "OPTIONS")
  if(NOT ARG_TARGET OR NOT ARG_INPUT OR NOT ARG_OUTPUT)
    message(FATAL_ERROR "gamelib_add_shader: TARGET, INPUT and OUTPUT are required")
  endif()
  if(NOT TARGET ${ARG_TARGET})
    message(FATAL_ERROR "gamelib_add_shader: no such target '${ARG_TARGET}'")
  endif()
  if(GAMELIB_SHDC STREQUAL "GAMELIB_SHDC-NOTFOUND")
    message(FATAL_ERROR
      "gamelib_add_shader: no vendored sokol-shdc for host "
      "${CMAKE_HOST_SYSTEM_NAME}/${CMAKE_HOST_SYSTEM_PROCESSOR}. "
      "Set GAMELIB_SOKOL_SHDC to a sokol-shdc binary.")
  endif()
  # Beyond the unsupported-host sentinel above, nothing else has checked that
  # GAMELIB_SHDC actually names a usable binary: an empty value (which a
  # directory-scope bug could produce silently -- see the CACHE INTERNAL note
  # above), a stale GAMELIB_SOKOL_SHDC override, or a path to a file that was
  # never vendored would otherwise all reach add_custom_command() and either
  # fail with an opaque generator error or silently build a no-op rule.
  if(NOT GAMELIB_SHDC OR NOT EXISTS "${GAMELIB_SHDC}")
    message(FATAL_ERROR
      "gamelib_add_shader: sokol-shdc binary not found at '${GAMELIB_SHDC}'. "
      "If you set GAMELIB_SOKOL_SHDC, check that it still points at a real "
      "binary; otherwise the vendored copy is missing -- run "
      "'tools/vendor.py check'.")
  endif()
  if(NOT ARG_SLANG)
    set(ARG_SLANG "${GAMELIB_SHDC_SLANG}")
  endif()
  if(ARG_SLANG STREQUAL "")
    # Same empty-SLANG symptom, two different causes: the dummy backend has no
    # shader language, but GAMELIB_SOKOL_BACKEND_RESOLVED is also unset when
    # GAMELIB_SOKOL=OFF kept libs/sokol from ever running and resolving a
    # backend at all -- that user never chose dummy and should not be told so.
    if("${GAMELIB_SOKOL_BACKEND_RESOLVED}" STREQUAL "")
      message(FATAL_ERROR
        "gamelib_add_shader: no sokol backend is resolved (GAMELIB_SOKOL is "
        "OFF, so libs/sokol was never processed). Enable GAMELIB_SOKOL or "
        "pass SLANG explicitly.")
    else()
      message(FATAL_ERROR
        "gamelib_add_shader: backend '${GAMELIB_SOKOL_BACKEND_RESOLVED}' has no "
        "shader language. The dummy backend cannot compile shaders; pass SLANG "
        "explicitly or select a real backend.")
    endif()
  endif()

  set(_in  "${CMAKE_CURRENT_SOURCE_DIR}/${ARG_INPUT}")
  set(_out "${CMAKE_CURRENT_BINARY_DIR}/${ARG_OUTPUT}")
  set(_dep "${_out}.d")

  # DEPENDS names three things, and all three matter:
  #   the .glsl input;
  #   the sokol-shdc binary, so re-vendoring the tool regenerates every shader
  #     rather than leaving output from the old compiler;
  #   via DEPFILE, whatever the shader @includes -- filesystem includes cannot
  #     be enumerated in CMake, so the compiler reports them itself.
  add_custom_command(
    OUTPUT  "${_out}"
    COMMAND "${GAMELIB_SHDC}" --input "${_in}" --output "${_out}"
            --slang "${ARG_SLANG}" --dependency-file "${_dep}" ${ARG_OPTIONS}
    DEPENDS "${_in}" "${GAMELIB_SHDC}"
    DEPFILE "${_dep}"
    COMMENT "sokol-shdc ${ARG_INPUT} -> ${ARG_OUTPUT} (${ARG_SLANG})"
    VERBATIM)

  # Attach to the named target rather than declaring add_custom_target(... ALL):
  # an ALL target would build regardless of what the consumer selected, and a
  # target name derived from the output filename collides the moment two
  # examples both produce shader.h.
  target_sources(${ARG_TARGET} PRIVATE "${_out}")
  target_include_directories(${ARG_TARGET} PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
endfunction()
