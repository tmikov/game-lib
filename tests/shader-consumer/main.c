/* Never calls sg_setup(): there is no GPU context to make that safe under
   a real backend here (unlike the dummy-backend headless-gfx test), and
   this project only needs to prove that gamelib_add_shader() produced a
   header that compiles and links from a genuine consumer's directory
   scope -- see tools/run_tests.py's shader_consumer scenario. */
#include <sokol/sokol_gfx.h>
#include "triangle.h"

int main(void) {
  return 0;
}
