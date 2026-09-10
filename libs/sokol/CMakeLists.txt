# --- backend selection -------------------------------------------------------
set(GAMELIB_SOKOL_BACKEND "auto" CACHE STRING
    "sokol rendering backend: auto|glcore|gles3|metal|d3d11|dummy")
set_property(CACHE GAMELIB_SOKOL_BACKEND PROPERTY STRINGS
             auto glcore gles3 metal d3d11 dummy)

set(_b ${GAMELIB_SOKOL_BACKEND})
if(_b STREQUAL "auto")
  if(EMSCRIPTEN)
    set(_b gles3)
  elseif(APPLE)
    set(_b metal)
  elseif(WIN32)
    set(_b d3d11)
  else()
    set(_b glcore)
  endif()
endif()

# Two parallel lists, not one flat name/macro list: list(FIND) on a flat list
# also matches macro slots (e.g. GAMELIB_SOKOL_BACKEND=SOKOL_GLCORE would find
# index 1 and silently pair to "gles3"), so an unsupported value must only ever
# be checked against the name slots.
set(_names  glcore       gles3      metal       d3d11       dummy)
set(_macros SOKOL_GLCORE SOKOL_GLES3 SOKOL_METAL SOKOL_D3D11 SOKOL_DUMMY_BACKEND)
list(FIND _names ${_b} _i)
if(_i EQUAL -1)
  message(FATAL_ERROR
    "GAMELIB_SOKOL_BACKEND=${GAMELIB_SOKOL_BACKEND} is not supported "
    "(expected one of: auto ${_names})")
endif()
list(GET _macros ${_i} GAMELIB_SOKOL_BACKEND_DEFINE)
message(STATUS "game-lib: sokol backend ${_b} (${GAMELIB_SOKOL_BACKEND_DEFINE})")

# Publish the resolved backend so cmake/GameLibShader.cmake (Task 11) can map it
# to a --slang value. An INTERNAL cache entry under the GAMELIB_ prefix, which
# the Global Constraints permit as an addition.
set(GAMELIB_SOKOL_BACKEND_RESOLVED "${_b}" CACHE INTERNAL "resolved sokol backend")

# --- sokol_gfx ---------------------------------------------------------------
# Its own link requirements, from sokol_gfx.h's "Link with the following system
# libraries" section -- which is separate from, and smaller than, sokol_app.h's.
gamelib_add_library(NAME sokol_gfx SOURCES src/sokol_gfx.c)
target_compile_definitions(gamelib_sokol_gfx PUBLIC ${GAMELIB_SOKOL_BACKEND_DEFINE})

if(APPLE)
  # sokol_app.h: "On macOS and iOS, the implementation must be compiled as
  # Objective-C." Applied to every sokol TU rather than per file: Objective-C is
  # a superset of C, so it is harmless where unneeded, and a per-file rule breaks
  # silently the day a backend change makes another TU touch a platform API.
  target_compile_options(gamelib_sokol_gfx PRIVATE -x objective-c)
  if(_b STREQUAL "metal")
    target_link_libraries(gamelib_sokol_gfx PUBLIC "-framework Metal")
  elseif(_b STREQUAL "glcore")
    target_link_libraries(gamelib_sokol_gfx PUBLIC "-framework OpenGL")
  endif()
elseif(EMSCRIPTEN)
  target_link_options(gamelib_sokol_gfx INTERFACE -sUSE_WEBGL2=1)
elseif(UNIX)
  # glcore means GLX here: sokol defaults to GLX and we never set
  # SOKOL_FORCE_EGL. gles3 on Linux forces EGL, which needs EGL as well.
  if(_b STREQUAL "glcore")
    target_link_libraries(gamelib_sokol_gfx PUBLIC GL)
  elseif(_b STREQUAL "gles3")
    target_link_libraries(gamelib_sokol_gfx PUBLIC GLESv2 EGL)
  endif()
endif()
# Windows needs nothing: D3D11 deps come via #pragma comment, and the GL backend
# ships its own loader.

# --- sokol_log / sokol_time --------------------------------------------------
# Separate targets, not folded into sokol_app: stm_now() is what every frame loop
# needs, windowed or not, and making it reachable only by linking a windowing
# library would defeat the gfx/app split.
gamelib_add_header_library(NAME sokol_log  HEADER sokol/sokol_log.h  IMPL_DEFINE SOKOL_LOG_IMPL)
gamelib_add_header_library(NAME sokol_time HEADER sokol/sokol_time.h IMPL_DEFINE SOKOL_TIME_IMPL)
if(APPLE)
  target_compile_options(gamelib_sokol_log  PRIVATE -x objective-c)
  target_compile_options(gamelib_sokol_time PRIVATE -x objective-c)
endif()

# --- sokol_app ---------------------------------------------------------------
# Not declared under the dummy backend: sokol_app.h #errors unless one of
# SOKOL_METAL / SOKOL_GLCORE / SOKOL_D3D11 / SOKOL_GLES3 / SOKOL_WGPU /
# SOKOL_NOAPI is defined, and dummy is none of them.
if(_b STREQUAL "dummy")
  message(STATUS "game-lib: sokol_app not declared (backend is dummy)")
else()
  gamelib_add_library(NAME sokol_app SOURCES src/sokol_app.c LIBS gamelib::sokol_gfx)
  target_compile_definitions(gamelib_sokol_app PUBLIC ${GAMELIB_SOKOL_BACKEND_DEFINE})

  if(APPLE)
    target_compile_options(gamelib_sokol_app PRIVATE -x objective-c)
    # AppKit, not the older Cocoa.
    target_link_libraries(gamelib_sokol_app PUBLIC "-framework AppKit" "-framework QuartzCore")
  elseif(UNIX AND NOT EMSCRIPTEN)
    target_link_libraries(gamelib_sokol_app PUBLIC X11 Xi Xcursor dl m)
    # The literal flag, both compiling and linking (upstream issue #376). NOT
    # Threads::Threads: FindThreads documents that THREADS_PREFER_PTHREAD_FLAG
    # "has no effect if the system libraries provide the thread functions", and
    # on glibc 2.34+ pthread lives in libc, so the imported target would carry
    # no flag at all.
    target_compile_options(gamelib_sokol_app PUBLIC -pthread)
    target_link_options(gamelib_sokol_app PUBLIC -pthread)
  endif()
endif()

# --- sokol_audio -------------------------------------------------------------
# No dependency on gfx or app: a consumer can take sound and nothing else.
gamelib_add_library(NAME sokol_audio SOURCES src/sokol_audio.c)
if(APPLE)
  target_compile_options(gamelib_sokol_audio PRIVATE -x objective-c)
  target_link_libraries(gamelib_sokol_audio PUBLIC "-framework AudioToolbox")
elseif(UNIX AND NOT EMSCRIPTEN)
  # asound, plus the pthread flag: the ALSA backend calls pthread_create() and
  # pthread_join() directly.
  target_link_libraries(gamelib_sokol_audio PUBLIC asound)
  target_compile_options(gamelib_sokol_audio PUBLIC -pthread)
  target_link_options(gamelib_sokol_audio PUBLIC -pthread)
endif()
# Windows/MSVC needs nothing: libs come via #pragma comment.

# --- sokol_imgui -------------------------------------------------------------
# Needs sokol_app (absent under the dummy backend) and gamelib::imgui (absent
# when GAMELIB_IMGUI=OFF). Declared only when both are there.
gamelib_have_targets(_have_imgui_deps sokol_app imgui)
if(_have_imgui_deps)
  gamelib_add_library(NAME sokol_imgui SOURCES src/sokol_imgui.cc
      LIBS gamelib::sokol_app gamelib::sokol_gfx gamelib::imgui)
  if(APPLE)
    target_compile_options(gamelib_sokol_imgui PRIVATE -x objective-c++)
  endif()
else()
  message(STATUS "game-lib: sokol_imgui not declared (needs sokol_app and imgui)")
endif()
