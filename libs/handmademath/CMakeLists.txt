# Header-only, and v2 has NO implementation define -- everything is static
# inline -- so this is an interface library, not a generated TU.
gamelib_add_interface_library(NAME handmademath
    LIBS $<$<NOT:$<PLATFORM_ID:Windows>>:m>)
# libm because it includes <math.h> and calls sqrtf/sinf/cosf through HMM_SQRTF
# and friends. A consumer who redefines those macros does not need it, but the
# target cannot know that.
