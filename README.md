# game-lib

A SHA-pinned CMake bundle of eight third-party game libraries, plus the
`sokol-shdc` shader compiler, meant to be dropped into another project as a
git submodule and consumed with `add_subdirectory`. It vendors source, not
binaries: every dependency lives in this repository at an exact upstream
commit (see [Vendoring](#vendoring) and `tools/vendor.toml`), and there is no
`find_package` or package-manager dependency to resolve at configure time.

Bundled: [sokol](https://github.com/floooh/sokol) (gfx/app/log/time/audio/imgui),
[Dear ImGui](https://github.com/ocornut/imgui),
[miniaudio](https://github.com/mackron/miniaudio),
[stb](https://github.com/nothings/stb) (nine headers, one target each),
[Box2D v3](https://github.com/erincatto/box2d),
[EnTT](https://github.com/skypjack/entt),
[HandmadeMath](https://github.com/HandmadeMath/HandmadeMath),
[itlib](https://github.com/iboB/itlib).

Requires CMake 3.21+. The `tools/` scripts (vendoring, acceptance tests) need
Python 3.11+ and use only the standard library — neither is needed to build
game-lib itself, only to maintain or verify it.

## Quick start

```cmake
add_subdirectory(third_party/game-lib EXCLUDE_FROM_ALL)

add_executable(mygame WIN32 main.c)
target_link_libraries(mygame PRIVATE
    gamelib::sokol_app
    gamelib::sokol_gfx
    gamelib::sokol_log
    gamelib::stb_image)
```

`EXCLUDE_FROM_ALL` keeps game-lib's targets out of your default build target.
It is *not* "nothing compiles unless linked" — the whole of `libs/` is still
**processed at configure time** regardless of what you link, so a library's
CMake must never fail just because its own system dependencies (X11, ALSA,
...) are absent; only linking it actually compiles it. Link only
`gamelib::*` alias targets, never the underlying `gamelib_*` target names —
those are internal and unversioned.

Every target is namespaced, so a typo in what you link (`gamelib::sokol_gfxx`)
is a configure-time error, not a silent `-lsokol_gfxx` passed to the linker.

### `WIN32` if you link `gamelib::sokol_app`

`sokol_app.h` defines `SOKOL_WIN32_FORCE_WINMAIN` by default, so on Windows it
supplies `WinMain` and your `main()` is never called. A console-subsystem
executable therefore fails to *link* with `unresolved external symbol main`.
Declaring the target `add_executable(mygame WIN32 main.c)` puts it in the GUI
subsystem and fixes it; the `WIN32` keyword is ignored by every non-Windows
generator, so write it unconditionally.

game-lib deliberately does not do this for you. The subsystem is a property of
*your* executable, and the only lever a linked library could pull is the
global `CMAKE_WIN32_EXECUTABLE`, which would silently change every other
target in your project — exactly what "game-lib adds, it never changes"
forbids. Every windowed example is written `add_executable(... WIN32 ...)` for
the same reason, and an acceptance scenario keeps them that way.

## Options

All default `ON` except where noted, and only gate whether a library's
`CMakeLists.txt` is even entered — set one `OFF` before `add_subdirectory` to
stop that library from being configured at all:

| option | default | effect |
|---|---|---|
| `GAMELIB_SOKOL` | `ON` | sokol targets |
| `GAMELIB_IMGUI` | `ON` | Dear ImGui target |
| `GAMELIB_MINIAUDIO` | `ON` | miniaudio target |
| `GAMELIB_STB` | `ON` | stb targets |
| `GAMELIB_BOX2D` | `ON` | Box2D target |
| `GAMELIB_ENTT` | `ON` | EnTT target |
| `GAMELIB_HANDMADEMATH` | `ON` | HandmadeMath target |
| `GAMELIB_ITLIB` | `ON` | itlib target |
| `GAMELIB_SOKOL_BACKEND` | `auto` | `auto`\|`glcore`\|`gles3`\|`metal`\|`d3d11`\|`dummy` — see [sokol backends](#sokol-backends) |
| `GAMELIB_MINIAUDIO_RUNTIME_LINKING` | `OFF` | macOS only: `ON` links CoreAudio frameworks at run time instead of link time (upstream's default, but not notarization-friendly) |
| `GAMELIB_BOX2D_AVX2` | `OFF` | compile Box2D with AVX2 (binaries then fault on pre-AVX2 hardware) |
| `GAMELIB_SOKOL_SHDC` | unset | override the vendored `sokol-shdc` binary path used by `gamelib_add_shader()` |

A library that is `OFF`, or whose declaration depends on something that
isn't there (e.g. `sokol_imgui` needs both `sokol_app` and `imgui`), is
simply not declared. Configure output prints a `STATUS` line naming every
target it skipped and why. There is no override: linking an undeclared
target is CMake's own missing-target error at generation time.

## Targets

Every consumer-visible target is an `ALIAS`; the real target name is
`gamelib_<name>` (used only for internal CMake dependencies and CI's
`cmake --build ... --target` invocations — never link it directly).

| `gamelib::` target | include as | language |
|---|---|---|
| `sokol_gfx` | `<sokol/sokol_gfx.h>` | C |
| `sokol_app` | `<sokol/sokol_app.h>` | C |
| `sokol_log` | `<sokol/sokol_log.h>` | C |
| `sokol_time` | `<sokol/sokol_time.h>` | C |
| `sokol_audio` | `<sokol/sokol_audio.h>` | C |
| `sokol_imgui` | `<sokol/sokol_imgui.h>` | **C++11** |
| `imgui` | `<imgui/imgui.h>` | **C++11** |
| `miniaudio` | `<miniaudio/miniaudio.h>` | C |
| `stb_image` | `<stb/stb_image.h>` | C |
| `stb_image_write` | `<stb/stb_image_write.h>` | C |
| `stb_truetype` | `<stb/stb_truetype.h>` | C |
| `stb_rect_pack` | `<stb/stb_rect_pack.h>` | C |
| `stb_ds` | `<stb/stb_ds.h>` | C |
| `stb_sprintf` | `<stb/stb_sprintf.h>` | C |
| `stb_perlin` | `<stb/stb_perlin.h>` | C |
| `stb_easy_font` | `<stb/stb_easy_font.h>` | C |
| `stb_vorbis` | see [stb_vorbis](#stb_vorbis-is-different) | C |
| `box2d` | `<box2d/box2d.h>` | **C17** |
| `entt` | `<entt/entt.hpp>` | **C++20** |
| `handmademath` | `<handmademath/HandmadeMath.h>` | C |
| `itlib` | one of 36 headers, e.g. `<itlib/span.hpp>` | **C++11 floor** — see [itlib's per-header standard](#itlibs-per-header-standard) |

`sokol_app` links `gamelib::sokol_gfx` publicly and is not declared under the
`dummy` backend (see [sokol backends](#sokol-backends)). `sokol_imgui` links
`sokol_app`, `sokol_gfx` and `imgui`, and is not declared unless all three are
available.

## C++ in an otherwise-C project

game-lib's own top-level `project()` call declares only `C`, and enables
`CXX` itself, internally, only if one of `GAMELIB_IMGUI`, `GAMELIB_ENTT` or
`GAMELIB_ITLIB` is `ON` — because CMake determines this at the point
`add_subdirectory(game-lib)` runs, before it has seen what you link. That
covers `imgui`, `sokol_imgui`, `entt` and `itlib`, the four `gamelib::`
targets that are C++.

The consequence: **if your own top-level project only declares `C`**
(`project(mygame LANGUAGES C)`) and you link any of those four targets, your
build will fail — not inside game-lib, but at your own `add_executable`, with
CMake unable to compile a `.cpp`/`.cc` file because `CXX` was never enabled
anywhere above it. Declare `CXX` yourself:

```cmake
project(mygame LANGUAGES C CXX)
```

or, if only a subdirectory of your own project needs it,
`enable_language(CXX)` there before anything C++ is compiled.

### Avoiding C++ compiler detection entirely

Some consumers (cross-compiling to an exotic C-only toolchain, wanting the
fastest possible empty-project configure) want to guarantee no C++ compiler
is ever probed. That requires all three of:

```cmake
set(GAMELIB_IMGUI OFF)
set(GAMELIB_ENTT OFF)
set(GAMELIB_ITLIB OFF)
```

before `add_subdirectory(game-lib)`. Linking only C targets (`sokol_app`,
`box2d`, `stb_image`, ...) is **not** enough by itself: the decision to call
`enable_language(CXX)` is made once, at configure time, from the three
options above — not from what ends up linked. Leaving any of the three `ON`
enables `CXX` regardless of whether you ever link `gamelib::imgui`,
`gamelib::entt` or `gamelib::itlib`.

## sokol backends

`GAMELIB_SOKOL_BACKEND` selects the rendering backend. `auto` (the default)
resolves to `metal` on macOS, `d3d11` on Windows, `glcore` on Linux, `gles3`
under Emscripten.

`dummy` is the odd one out: it is a **gfx-only** backend. `sokol_app.h`
itself `#error`s unless a real backend macro is defined, so under
`GAMELIB_SOKOL_BACKEND=dummy`, `gamelib::sokol_app` and `gamelib::sokol_imgui`
(and any example needing either) are simply not declared. `gamelib::sokol_gfx`,
`gamelib::sokol_log`, `gamelib::sokol_time` and `gamelib::sokol_audio` are
unaffected. This is what makes a fully headless configure/build possible —
`GAMELIB_SOKOL_BACKEND=dummy` pulls in no X11, no GL, no windowing library at
all, which is exactly what the `headless` CI job (below) exercises.

### `sokol_gfx.h` before `sokol_glue.h`

`sokol_glue.h` declaratively depends on `sokol_gfx.h` and `#error`s if you
include it first:

```c
#include <sokol/sokol_gfx.h>   /* must come first */
#include <sokol/sokol_app.h>
#include <sokol/sokol_glue.h>  /* binds app + gfx together */
```

## `stb_vorbis` is different

Every other stb target is used as `#include <stb/stb_image.h>` and so on.
`gamelib::stb_vorbis` is the one exception, because upstream ships it as a
`.c` file, not a header. Include it the way upstream documents:

```c
#define STB_VORBIS_HEADER_ONLY
#include <stb/stb_vorbis.c>
```

### stb_vorbis and miniaudio do not compose automatically

miniaudio's built-in decoders cover WAV, MP3 and FLAC — not Ogg Vorbis.
Linking both `gamelib::miniaudio` and `gamelib::stb_vorbis` does **not** by
itself make `ma_engine` or `ma_decoder` read `.ogg` files: this pack declares
them as two independent targets, and `gamelib::miniaudio`'s own translation
unit never includes `stb_vorbis.c`, so nothing wires the two together for
you (doing that here would couple two targets this pack keeps separate on
purpose). Two workflows are actually supported:

1. **Decode with stb_vorbis, hand miniaudio the PCM.** Decode the whole file
   (or stream it) with `stb_vorbis_decode_memory`/`stb_vorbis_decode_filename`
   or the pull API, then feed the resulting samples to miniaudio through
   `ma_audio_buffer` or your own `ma_data_source`.
2. **Let miniaudio's own stb_vorbis adapter compile in.** `miniaudio.h`
   already ships a complete `ma_decoding_backend_vtable` for stb_vorbis
   (search it for `STB_VORBIS_INCLUDE_STB_VORBIS_H` / `MA_HAS_VORBIS` /
   `g_ma_decoding_backend_vtable_stbvorbis`) — you do not need to write one.
   It compiles in automatically when, in the **same translation unit** that
   defines `MINIAUDIO_IMPLEMENTATION` and includes `<miniaudio/miniaudio.h>`,
   `stb_vorbis.h`'s own include guard (`STB_VORBIS_INCLUDE_STB_VORBIS_H`) is
   already defined — i.e. you included
   `<stb/stb_vorbis.c>` (with `STB_VORBIS_HEADER_ONLY`, per
   [stb_vorbis is different](#stb_vorbis-is-different)) before
   `<miniaudio/miniaudio.h>` in that TU. Once `MA_HAS_VORBIS` is defined this
   way, `ma_decoder_init*`/`ma_engine_play*` pick `.ogg` files up through
   their normal format auto-detection — no `ppCustomBackendVTables`
   registration needed. This pack does not do this wiring for you: doing so
   in `gamelib::miniaudio`'s own implementation TU would force every
   consumer of `gamelib::miniaudio` to also compile `stb_vorbis.c`, coupling
   two targets that are deliberately independent. Set it up in your own
   game's translation unit if you want it.

Do not assume the two targets compose without one of the above.

## itlib's per-header standard

`gamelib::itlib` declares a **floor** of C++11 (`target_compile_features(...
INTERFACE cxx_std_11)`), not a ceiling — because itlib is header-only and
different headers need different standards. Including one of the five
listed below without your own target being on at least that standard
produces an incomprehensible compiler error deep in the header, not a clean
"needs C++17" message:

| header | minimum standard |
|---|---|
| every other header (31 of 36) | C++11 |
| `pmr_allocator.hpp` | C++17 |
| `rand_dist.hpp` | C++17 |
| `strutil.hpp` | C++17 |
| `generator.hpp` | C++20 |
| `opt_ref_buffer.hpp` | C++20 |

If your target includes `generator.hpp` or `opt_ref_buffer.hpp`, raise your
own target's standard:

```cmake
target_compile_features(mygame PRIVATE cxx_std_20)
```

## Emscripten: don't set a C standard flag yourself

Under Emscripten, `gamelib::miniaudio` clears its own target's `C_STANDARD`
property, because miniaudio's own documentation states you cannot use
`-std=c*` (or `-ansi`) compiler flags with it under Emscripten. That protects
against `CMAKE_C_STANDARD` being set before `add_subdirectory(game-lib)` —
CMake initialises every new target's `C_STANDARD` from that variable, and
game-lib's own target is not exempt from inheriting it unless explicitly
cleared. **What game-lib cannot fix:** a `-std=c*` flag you put directly into
`CMAKE_C_FLAGS` (rather than `CMAKE_C_STANDARD`) reaches every target's
compile line, miniaudio's included, and there is no target-level property
that can undo a flag baked into a global variable. If you build for
Emscripten, keep `-std=` out of `CMAKE_C_FLAGS`.

## Abseil

game-lib does not vendor [Abseil](https://github.com/abseil/abseil-cpp).
Nothing in this pack uses it, and it already has first-class CMake and
`find_package` support plus packages in vcpkg, conan and most distros — there
is no vendoring gap to fill. Vendoring it anyway would cost real
compatibility: Abseil declares hundreds of `absl::*` targets (24 in
`absl/strings/` alone), and CMake hard-errors on a duplicate target name, so
a consumer who already brings their own Abseil could not add game-lib
alongside it.

If you want it, bring it yourself and link it next to game-lib the ordinary
way:

```cmake
find_package(absl CONFIG REQUIRED)
add_subdirectory(third_party/game-lib EXCLUDE_FROM_ALL)

target_link_libraries(mygame PRIVATE
    gamelib::sokol_app gamelib::box2d
    absl::span)              # theirs, not ours
```

For the two facilities most consumers actually reach for Abseil for —
`absl::Span` and `absl::InlinedVector` — `gamelib::itlib` covers both, as
`itlib/span.hpp` and `itlib/small_vector.hpp`, in two headers instead of
Abseil's 1500+.

## Shader compilation

`cmake/GameLibShader.cmake` (included automatically) provides
`gamelib_add_shader()`, a thin wrapper around the vendored `sokol-shdc`
binary for the host platform:

```cmake
gamelib_add_shader(TARGET mygame INPUT shader.glsl OUTPUT shader.h)
```

- `TARGET` must already exist (declare it with `add_executable`/`add_library`
  first). The generated header is added to that target's sources, and the
  calling directory's binary directory (where the header lands) to that
  target's private include path.
- `INPUT`/`OUTPUT` are paths relative to the calling `CMakeLists.txt`'s
  source/binary directory.
- `SLANG` defaults to whatever `--slang` upstream documents for the
  currently-resolved `GAMELIB_SOKOL_BACKEND` (e.g. `glsl410` for `glcore`,
  `hlsl5` for `d3d11`); pass it explicitly to override.
- `OPTIONS` passes any extra flags straight through to `sokol-shdc`.
- Editing the `.glsl`, or any file it `@include`s, regenerates the header on
  the next build — dependencies are tracked through a compiler-generated
  `--dependency-file`, not guessed.
- The `dummy` backend has no shader language at all (`GAMELIB_SHDC_SLANG` is
  empty), so `gamelib_add_shader()` fails configure with a clear error under
  it unless you pass `SLANG` explicitly.

See `examples/shader/` for a complete, working example.

## Examples

Built only when `game-lib` is the top-level project (never inside a
consumer's build), and only when every target they need was declared:

| example | exercises |
|---|---|
| `clear` | `sokol_app` + `sokol_gfx` + `sokol_log` + `sokol_time` — a window with a pulsing clear colour |
| `image` | + `stb_image` — decode an embedded PNG into a texture |
| `imgui` | `sokol_imgui` + `imgui` — the Dear ImGui demo window |
| `beep` | `sokol_audio` — push a generated tone to the device |
| `audio` | `miniaudio` — play a synthesised buffer through `ma_engine` |
| `physics` | `box2d` — a box falling onto static ground, stepped and printed to stdout; headless, no renderer |
| `shader` | `gamelib_add_shader()` end to end — compile a `.glsl` and draw a shaded triangle |

`entt`, `handmademath` and `itlib` have no example: they are header-only with
no initialisation and no interaction with the rest of the pack, so an
example would demonstrate upstream's API rather than anything about
game-lib. `tests/compile-includes/` exercises their include paths instead.

Windowed examples (`clear`, `image`, `imgui`, `shader`) need a display to
*run*; CI only builds them.

## Vendoring

`tools/vendor.toml` is the single source of truth for what is vendored and
at which upstream commit. `tools/vendor.py`:

- `list` — print every entry and its pinned revision.
- `check` — verify the working tree matches the manifest (hashes every
  vendored file); exits non-zero on drift.
- `update <name>` — re-vendor one dependency at a newer ref.

## Licences

game-lib's own code -- the CMake, `tools/`, the examples and the docs -- is MIT;
see `LICENSE`. Everything else here belongs to its upstream author and keeps its
own terms.

All of them are permissive and none is copyleft, so nothing constrains what you
license your own project as. What they do require is that their notices travel
with the code:

| dependency | licence | obliges you to |
|---|---|---|
| Dear ImGui, Box2D, EnTT, itlib | MIT | reproduce the notice in copies and substantial portions |
| sokol | zlib | not misrepresent origin; mark altered versions. No binary-distribution notice required |
| miniaudio | Unlicense **or** MIT-0, your choice | nothing, under either |
| stb | Unlicense **or** MIT, your choice | nothing, under the public-domain option |
| HandmadeMath | CC0 | nothing |
| sokol-shdc (the vendored binaries) | MIT, **plus** the licences of what is linked into them | see below |

Each dependency's own text is vendored beside it at `libs/<name>/LICENSE`, and
`tools/sokol-shdc/LICENSE` for the tool.

### Shipping a binary

A compiled game carries no `libs/` tree, so the notices above have to come from
somewhere else. **`THIRD-PARTY-NOTICES.md`** at the repository root is that
somewhere: every licence in this repository, aggregated into one file you can
paste into an about-box or a docs page. It is generated by
`python3 tools/vendor.py notices`, and `vendor.py check` fails if it has gone
stale, so it cannot drift away from what is actually vendored.

### The sokol-shdc binaries carry more than their own licence

`tools/sokol-shdc/bin/` holds prebuilt executables, and a prebuilt executable
redistributes everything statically linked into it. Those binaries contain
glslang, Tint, SPIRV-Cross, SPIRV-Tools and fmt -- SPIRV-Tools and SPIRV-Cross
are Apache-2.0, and Apache-2.0 section 4 governs redistribution in *object*
form, which is precisely what shipping a binary is.

Upstream's `sokol-tools-bin` ships only its author's MIT licence and names none
of these, so that notice alone is not sufficient. Their texts are therefore
vendored at `tools/sokol-shdc/third-party-licenses/` and included in
`THIRD-PARTY-NOTICES.md`.

One honest limitation: upstream publishes no record of which `sokol-tools`
revision built a given `sokol-tools-bin` commit, so these texts are each
dependency's current licence rather than the exact revision compiled into the
binaries. Each file records the revision it was fetched from. If that matters
for your distribution, build `sokol-shdc` yourself and set `GAMELIB_SOKOL_SHDC`.

This is not legal advice.

## CI

`.github/workflows/build.yml` runs two jobs on every push and pull request:

- **desktop** — `ubuntu-latest`, `macos-latest`, `windows-latest`. Runs
  `tools/vendor.py check`, then the full acceptance suite
  (`tools/run_tests.py`), which configures and builds game-lib as a
  top-level project (all examples) plus every acceptance scenario.
- **headless** — a `debian:bookworm-slim` container with a compiler, CMake
  and Python installed and **no X11 development packages at all**.
  Configures with `GAMELIB_SOKOL_BACKEND=dummy` and builds
  `gamelib_sokol_gfx`, `gamelib_box2d` and `gamelib_stb_image`, then
  separately configures, builds and **runs** `tests/headless-gfx/` — a real
  `add_executable()` that calls `sg_setup()`/`sg_shutdown()`. The static-library
  build alone cannot prove a link ever succeeds (`target_link_libraries()` on
  a `STATIC` library never invokes the linker), so the executable is the
  actual regression test for the gfx/app split described above: if it ever
  starts requiring an X11 dev package, something pulled a windowing
  dependency into a target that is supposed to be headless.

## Running the acceptance suite locally

```sh
python3 tools/vendor.py check
python3 tools/run_tests.py
```
