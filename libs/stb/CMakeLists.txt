# Nine targets, one per header, so a consumer wanting stb_image does not compile
# stb_truetype. Eight are generated from the list below; stb_vorbis is the
# exception, shipped upstream as a .c rather than a header.

set(GAMELIB_STB_HEADERS
  stb_image          STB_IMAGE_IMPLEMENTATION
  stb_image_write    STB_IMAGE_WRITE_IMPLEMENTATION
  stb_truetype       STB_TRUETYPE_IMPLEMENTATION
  stb_rect_pack      STB_RECT_PACK_IMPLEMENTATION
  stb_ds             STB_DS_IMPLEMENTATION
  stb_sprintf        STB_SPRINTF_IMPLEMENTATION
  stb_perlin         STB_PERLIN_IMPLEMENTATION
  stb_easy_font      STB_EASY_FONT_IMPLEMENTATION
)

# libm uniformly on the three non-Windows platforms rather than auditing each
# header per release. stb_image alone would justify it (pow, ldexp). It
# over-declares for a header needing no math; it hides no correctness question.
set(GAMELIB_STB_LIBS $<$<NOT:$<PLATFORM_ID:Windows>>:m>)

list(LENGTH GAMELIB_STB_HEADERS _n)
math(EXPR _last "${_n} / 2 - 1")
foreach(i RANGE ${_last})
  math(EXPR _ni "${i} * 2")
  math(EXPR _di "${i} * 2 + 1")
  list(GET GAMELIB_STB_HEADERS ${_ni} _name)
  list(GET GAMELIB_STB_HEADERS ${_di} _def)
  gamelib_add_header_library(
    NAME        ${_name}
    HEADER      stb/${_name}.h
    IMPL_DEFINE ${_def}
    LIBS        ${GAMELIB_STB_LIBS})
endforeach()

# Upstream ships stb_vorbis as a .c. Consumers include it upstream-style:
#   #define STB_VORBIS_HEADER_ONLY
#   #include <stb/stb_vorbis.c>
gamelib_add_library(
  NAME    stb_vorbis
  SOURCES stb/stb_vorbis.c
  LIBS    ${GAMELIB_STB_LIBS})
