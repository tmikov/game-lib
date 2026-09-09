/* The regression test for the gfx/app split: this links a real executable
   against gamelib::sokol_gfx under the dummy backend, in an environment
   with no X11 development packages. target_link_libraries() on a STATIC
   library (what gamelib_sokol_gfx is) never invokes the linker, so building
   only static libraries -- as the headless CI job used to do -- can never
   prove that sokol_gfx's PUBLIC link interface stayed free of a windowing
   dependency. An add_executable() forces an actual link. */
#include <sokol/sokol_gfx.h>
#include <sokol/sokol_log.h>

int main(void) {
  sg_setup(&(sg_desc){ .logger.func = slog_func });
  int ok = sg_isvalid();
  sg_shutdown();
  return ok ? 0 : 1;
}
