# Box2D v3 -- a rewrite in C, unrelated to the 2.x C++ API.
#
# The dependency contract below is specific to v3.1.1 and MUST be re-derived on
# update: upstream's in-development 3.2.0 adds src/scheduler.c and
# src/parallel_for.c with a built-in worker pool calling b2CreateThread /
# b2JoinThread, files that do not exist at v3.1.1. Note that grepping for
# "pthread" is the wrong check -- 3.2.0 spawns threads through its own
# abstraction and such a grep finds nothing. Search for thread *creation*.
file(GLOB GAMELIB_BOX2D_SOURCES CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/box2d/src/*.c")

gamelib_add_library(NAME box2d SOURCES ${GAMELIB_BOX2D_SOURCES})
target_compile_features(gamelib_box2d PUBLIC c_std_17)

# libm: src/ makes 22 calls to sqrtf/cosf/sinf/atan2f. Nothing else -- v3.1.1
# has no thread creation of any spelling; its multithreading is entirely
# user-supplied through b2WorldDef's task callbacks.
target_link_libraries(gamelib_box2d PUBLIC $<$<NOT:$<PLATFORM_ID:Windows>>:m>)

# src/*.h include "box2d/math_functions.h" -- prefixed, so quote-relative lookup
# fails and it falls through to the include path, where the PUBLIC root resolves
# it. Siblings ("array.h") resolve quote-relative. Hence no PRIVATE entry.

option(GAMELIB_BOX2D_AVX2 "Compile Box2D with AVX2" OFF)
if(GAMELIB_BOX2D_AVX2)
  # Off by default: AVX2 binaries fault on pre-AVX2 hardware, the wrong default
  # for a library shipped to unknown machines. SSE2 on x86-64 and NEON on arm64
  # are upstream's baseline and need no flag.
  target_compile_definitions(gamelib_box2d PRIVATE BOX2D_AVX2)
  if(MSVC)
    target_compile_options(gamelib_box2d PRIVATE /arch:AVX2)
  else()
    target_compile_options(gamelib_box2d PRIVATE -mavx2)
  endif()
endif()

if(EMSCRIPTEN)
  target_compile_options(gamelib_box2d PRIVATE -msimd128 -msse2)
endif()
