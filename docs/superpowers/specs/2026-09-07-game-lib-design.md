# game-lib — design

Date: 2026-09-07
Status: approved, ready for implementation planning

Research inputs: [apple2tc.md](../../../apple2tc.md),
[imgui-react-runtime.md](../../../imgui-react-runtime.md).

## 1. Purpose and scope

`game-lib` is a curated, SHA-pinned bundle of third-party game libraries with
CMake targets, consumed by other projects as a git submodule. A consumer links
only what it wants; everything else costs nothing.

**It contains no original runtime code.** The singular `lib/` directory is
reserved and stays empty: if the pack later grows a thin app-shell layer (the
sokol lifecycle, imgui wiring and frame pacing that every project retypes), that
is where it goes, and it is a separate design.

Four upstream projects:

| project | licence | what we take |
|---|---|---|
| [sokol](https://github.com/floooh/sokol) | zlib | app, gfx, glue, log, time, audio, util/imgui |
| [Dear ImGui](https://github.com/ocornut/imgui) | MIT | core (no backends — sokol_imgui is the backend) |
| [SoLoud](https://github.com/jarikomppa/soloud) | zlib | include/ + src/ (core, audiosource, filter, backend) |
| [stb](https://github.com/nothings/stb) | MIT / public domain | 9 headers, listed in §5.4 |

Deliberately excluded: **cimgui** (needed only to call ImGui from C or to bind
an FFI; our sokol_imgui bridge TU is C++, so plain Dear ImGui suffices) and
**sokol_gl**.

Platforms: Linux, macOS, Windows, Emscripten. Not Android, not iOS.

## 2. Repository layout

```
game-lib/
  CMakeLists.txt              option gates, add_subdirectory(libs), examples
  cmake/
    GameLibLibrary.cmake      gamelib_add_library(), gamelib_add_header_library(),
                              gamelib_add_example()
    single_header_impl.c.in   template for generated single-header impl TUs
  libs/
    CMakeLists.txt            option-gated add_subdirectory lines, nothing else
    sokol/
      CMakeLists.txt
      VERSION                 generated; url + commit + date
      LICENSE                 upstream, verbatim
      sokol/                  verbatim upstream headers
      src/                    our impl TUs
    imgui/
      CMakeLists.txt  VERSION  LICENSE
      imgui/                  verbatim upstream (headers and .cpp together)
    soloud/
      CMakeLists.txt  VERSION  LICENSE
      soloud/                 upstream include/
      src/                    upstream src/{core,audiosource,filter,backend}
    stb/
      CMakeLists.txt  VERSION  LICENSE
      stb/                    verbatim upstream headers
  examples/
    CMakeLists.txt
    clear/  imgui/  beep/  soloud/  image/
  tools/
    vendor.py
    vendor.toml               the single source of truth for pinning
  docs/
  lib/                        reserved, empty (see §1)
  LICENSE                     game-lib's own (MIT)
  README.md
```

### 2.1 The `libs/<name>/<name>/` doubling

Upstream files land in a directory *named after the library*, and the target's
public include directory is that directory's **parent**. This single decision
buys three things:

1. **Namespaced includes.** The consumer writes `#include <sokol/sokol_gfx.h>`,
   `<imgui/imgui.h>`, `<soloud/soloud.h>`, `<stb/stb_image.h>`. A pack that
   dumps thirty headers into the consumer's global include space is antisocial;
   this makes the origin of every header obvious at the use site.
2. **Upstream files are never edited or renamed.** Upstream's own sibling
   includes (`imgui.cpp` → `"imgui.h"`, `imgui.h` → `"imconfig.h"`) resolve by
   quote-relative lookup because those files stay in one directory together.
3. **Wholesale replacement on update.** `vendor.py` can `rm -rf libs/sokol/sokol`
   and re-copy, with no risk of leaving a deleted upstream file behind.

This is the `include/<lib>/` refinement identified in
[apple2tc.md §6](../../../apple2tc.md) — present in neither surveyed repo —
without the file-relocation cost that made it awkward there.

**SoLoud** is the one library that additionally needs a **PRIVATE** include
directory, because its sources sit beside rather than inside that directory.
(Our own `libs/sokol/src/*.c` do too, but they are ours to write, so they use the
`<sokol/...>` form and the PUBLIC root already covers them.)

- `libs/soloud/src/**/*.cpp` — upstream sources that include `"soloud.h"` bare.
  These need `PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/soloud`. SoLoud's audiosource
  files also include its own bundled `"stb_vorbis.h"`, `"dr_wav.h"`,
  `"dr_mp3.h"`, `"dr_flac.h"`, which live beside them inside
  `src/audiosource/wav/` — quote-relative, and **private**, so SoLoud's bundled
  stb_vorbis never collides with `gamelib::stb_vorbis`.

## 3. The consumer contract

```cmake
add_subdirectory(third_party/game-lib EXCLUDE_FROM_ALL)

add_executable(mygame main.c)
target_link_libraries(mygame PRIVATE
    gamelib::sokol_app
    gamelib::sokol_time
    gamelib::sokol_audio
    gamelib::stb_image)
```

### 3.1 Target naming

Real target names are prefixed — `gamelib_sokol_app` — and every one gets an
`ALIAS gamelib::sokol_app`. Consumers are documented to use only the `::` form.

Prefixing is not cosmetic. A bare `sokol` target would collide fatally with a
consumer that already vendors sokol itself. And CMake hard-errors on an unknown
`ns::name` while silently passing an unknown bare name through to the linker as
`-lwhatever`, so the namespaced form turns a typo into a configure error.

### 3.2 Selection: link-driven, with options as an escape hatch

- `EXCLUDE_FROM_ALL` on the `add_subdirectory` means **nothing compiles unless
  linked**. SoLoud sitting in the tree costs a consumer who never links it zero
  build time. Choosing a library *is* naming it in `target_link_libraries`.
- Per-library options default `ON` and exist only so a consumer can stop a
  library's CMake being parsed at all:
  `GAMELIB_SOKOL`, `GAMELIB_IMGUI`, `GAMELIB_SOLOUD`, `GAMELIB_STB`.
- Configuration options, where a library genuinely has a choice:
  - `GAMELIB_SOKOL_BACKEND` = `auto` (default) | `glcore` | `gles3` | `metal` |
    `d3d11` | `dummy`. `auto` resolves to metal on macOS, d3d11 on Windows,
    glcore on Linux, gles3 on Emscripten. `dummy` selects
    `SOKOL_DUMMY_BACKEND`, which is what makes a headless/CI build possible.
  - `GAMELIB_SOLOUD_BACKEND` = `miniaudio` (default) | `alsa` | `coreaudio` |
    `wasapi` | `sdl2` | `null` | `nosound`. miniaudio is the default because it
    is the only backend that works on all three desktop platforms with no
    system development package installed.

### 3.3 The hard rule: a submodule never mutates global state

Prohibited anywhere in this repo:

- `include_directories()`, `add_definitions()`, `link_libraries()`
- setting `CMAKE_CXX_STANDARD`, `CMAKE_C_STANDARD`, `CMAKE_*_FLAGS`
- setting `CMAKE_EXECUTABLE_SUFFIX`

The last one is not hypothetical: `imgui-react-runtime`'s sokol CMakeLists does
`set(CMAKE_EXECUTABLE_SUFFIX ".html")` under Emscripten. Inside a submodule that
would silently rename *the consumer's* binaries.

Everything is expressed with `target_*` commands. Language requirements become
`target_compile_features(gamelib_imgui PUBLIC cxx_std_11)`. Emscripten's WebGL2
requirement becomes
`target_link_options(gamelib_sokol_app INTERFACE -sUSE_WEBGL2=1)`, so a consumer
inherits the flag by linking rather than by reading documentation.

This rule is testable; see §8, criterion 6.

## 4. Target catalogue

| target | sources | depends on | system links |
|---|---|---|---|
| `gamelib::sokol_gfx` | `src/sokol_gfx.c` | — | none (backend define only) |
| `gamelib::sokol_app` | `src/sokol_app.c` (app + glue) | `sokol_gfx` | see §5.1 |
| `gamelib::sokol_log` | generated TU | — | none |
| `gamelib::sokol_time` | generated TU | — | none |
| `gamelib::sokol_audio` | `src/sokol_audio.c` | — | Linux `asound`; macOS `AudioToolbox`; Windows/MSVC none |
| `gamelib::sokol_imgui` | `src/sokol_imgui.cc` (**C++**) | `sokol_app`, `sokol_gfx`, `imgui` | none |
| `gamelib::imgui` | 5 upstream `.cpp` | — | none |
| `gamelib::soloud` | upstream core/audiosource/filter + 1 backend | — | per backend; miniaudio needs none |
| `gamelib::stb_image` | generated TU | — | none |
| `gamelib::stb_image_write` | generated TU | — | none |
| `gamelib::stb_truetype` | generated TU | — | none |
| `gamelib::stb_rect_pack` | generated TU | — | none |
| `gamelib::stb_ds` | generated TU | — | none |
| `gamelib::stb_sprintf` | generated TU | — | none |
| `gamelib::stb_perlin` | generated TU | — | none |
| `gamelib::stb_easy_font` | generated TU | — | none |
| `gamelib::stb_vorbis` | `stb/stb_vorbis.c` directly | — | none |

### 4.1 Why sokol is split this finely

**`sokol_gfx` separate from `sokol_app`** is the one place granularity goes
beyond the obvious, and it is the point of the pack. Linking `gamelib::sokol_gfx`
with `GAMELIB_SOKOL_BACKEND=dummy` pulls **no X11, no GL, no windowing** — a
headless build, a unit test, a deterministic replay harness. That is exactly the
property apple2tc achieves by keeping `a2host` sokol-free, made available to a
consumer as a link-graph choice rather than a source-tree convention.

`sokol_glue` goes with `sokol_app` because it exists only to bind app and gfx
together; it has no meaning without both.

**`sokol_log` and `sokol_time` are their own targets** rather than riding along
in `sokol_app`. `stm_now()` is what every frame loop needs for timing, windowed
or not; making it reachable only by linking a windowing library would defeat the
split above. Each is a generated two-line TU with no dependencies.

### 4.2 Why nine stb targets

Each stb header compiles to its own TU, and each gets its own target, so a
consumer that wants `stb_image` does not compile `stb_truetype` and
`stb_vorbis`. Eight of the nine are *generated by a loop* over the list in
§5.4 — eight targets from eight list entries, not eight hand-written CMake
blocks. `stb_vorbis` is the exception: upstream ships it as a `.c`, so it is
compiled directly.

The alternative considered and rejected: one `gamelib::stb` static archive
containing nine objects, relying on the linker to pull only referenced members.
That yields the same binary, but still *compiles* all nine whenever any is
linked.

### 4.3 sokol_imgui is C++

`sokol_imgui.h` states (lines 17–20 of the header) that its implementation
compiled as C++ calls the Dear ImGui C++ API directly, and compiled as C calls
cimgui and hard-errors without `cimgui.h`. We own the impl TU, so we compile it
as C++ and cimgui is not needed. sokol itself remains pure C: a C game can link
`gamelib::sokol_app` and simply not use `sokol_imgui`.

## 5. Per-library specifics

### 5.1 sokol

Vendored headers (all flattened into `libs/sokol/sokol/`, collapsing upstream's
root vs `util/` split):

`sokol_app.h` `sokol_gfx.h` `sokol_glue.h` `sokol_log.h` `sokol_time.h`
`sokol_audio.h` `util/sokol_imgui.h`

Our TUs in `libs/sokol/src/`:

```c
/* src/sokol_gfx.c */
#define SOKOL_GFX_IMPL
#include <sokol/sokol_gfx.h>
```
```c
/* src/sokol_app.c */
#define SOKOL_APP_IMPL
#include <sokol/sokol_app.h>
/* glue needs the declarations of both, and its own impl macro. */
#include <sokol/sokol_gfx.h>
#define SOKOL_GLUE_IMPL
#include <sokol/sokol_glue.h>
```
```cpp
/* src/sokol_imgui.cc -- compiled as C++ so sokol_imgui calls the Dear ImGui
   C++ API directly and no cimgui is required.
   Include order below is required by sokol_imgui.h and must not be sorted:
   sokol_gfx.h and sokol_app.h before the declaration, imgui.h before the
   implementation. */
#include <sokol/sokol_gfx.h>
#include <sokol/sokol_app.h>

#include <imgui/imgui.h>

#define SOKOL_IMGUI_IMPL
#include <sokol/sokol_imgui.h>
```

Per-header impl macros (`SOKOL_GFX_IMPL`) rather than the blanket `SOKOL_IMPL`,
because the TUs are split.

Backend define is `PUBLIC` on both `sokol_gfx` and `sokol_app`. It must be:
`sokol_gfx.h` hard-errors without one (`#error "Please select a backend with
SOKOL_GLCORE, SOKOL_GLES3, SOKOL_D3D11, SOKOL_METAL, SOKOL_WGPU, SOKOL_VULKAN or
SOKOL_DUMMY_BACKEND"`). The check sits inside the `SOKOL_GFX_IMPL` block, so the
public declarations are backend-independent — but a consumer that includes
`sokol_gfx.h` and calls `sg_query_backend()` still wants the define to agree,
which `PUBLIC` guarantees.

**Note the renamed defines.** Current sokol uses `SOKOL_GLCORE` and
`SOKOL_GLES3`. `SOKOL_GLCORE33` and `SOKOL_GLES2` — what apple2tc and
imgui-react-runtime both pass — no longer exist. Neither repo's sokol CMakeLists
can be copied verbatim.

System libraries, from `sokol_app.h`'s own "Link with the following system
libraries" section:

- **Linux**, all backends: `X11 Xi Xcursor dl m`; with glcore add `GL`, with
  gles3 add `GLESv2`. Also requires `-pthread` as **both** a compile and a link
  option (upstream issue #376) — use
  `set(THREADS_PREFER_PTHREAD_FLAG ON)` + `find_package(Threads REQUIRED)` +
  `Threads::Threads`, which supplies both.
- **macOS**, all backends: `AppKit`, `QuartzCore`; with metal add `Metal`, with
  glcore add `OpenGL`. (Note `AppKit`, not the older `Cocoa` both surveyed repos
  use.) `sokol_app.h` states the implementation **must be compiled as
  Objective-C** on macOS. Rule: on Apple, compile **every** sokol impl TU as
  Objective-C — `-x objective-c` for the `.c` TUs and `-x objective-c++` for
  `sokol_imgui.cc` — via `target_compile_options(... PRIVATE ...)`, rather than
  maintaining duplicate `.m` files as apple2tc does. Applied uniformly on
  purpose: Objective-C is a superset of C, so it is harmless for a TU that does
  not need it, and a per-file rule would silently break the day a backend change
  makes another TU touch a platform API.
- **Windows** with MSVC or Clang: nothing — dependencies are declared in-source
  via `#pragma comment`. MinGW is out of scope for the initial version.
- **Emscripten**: `target_link_options(... INTERFACE -sUSE_WEBGL2=1)`.

`sokol_audio.h` links: Linux `asound`, macOS `AudioToolbox`, Windows/MSVC
nothing.

### 5.2 imgui

Vendored verbatim into `libs/imgui/imgui/`:
`imgui.h` `imconfig.h` `imgui_internal.h` `imstb_rectpack.h` `imstb_textedit.h`
`imstb_truetype.h` `imgui.cpp` `imgui_draw.cpp` `imgui_tables.cpp`
`imgui_widgets.cpp` `imgui_demo.cpp` `LICENSE.txt`

No `backends/` — sokol_imgui *is* the backend. `imgui_demo.cpp` is kept:
`ShowDemoWindow()` is genuinely used and it costs compile time only when linked.

`target_compile_features(gamelib_imgui PUBLIC cxx_std_11)`.

imgui's bundled `imstb_truetype.h` and our `stb/stb_truetype.h` differ in name,
so there is no collision even when both are linked.

### 5.3 soloud

- `libs/soloud/soloud/` ← upstream `include/*.h`
- `libs/soloud/src/` ← upstream `src/{core,audiosource,filter,backend}`,
  structure preserved
- Excluded: `demos/`, `docsrc/`, `contrib/`, `scripts/`, `glue/`, `build/`, and
  upstream's own `.gitmodules` — that last exclusion is what keeps game-lib
  exactly **one** submodule level deep for its consumers.
- `audiosource/openmpt` is excluded (requires external libopenmpt). All other
  audiosources are included.
- All backend sources are vendored, but only the selected one compiles —
  `soloud.cpp` gates each on `WITH_MINIAUDIO` / `WITH_ALSA` / `WITH_COREAUDIO` /
  `WITH_WASAPI` / … and hard-errors if none is defined. Switching backend
  therefore needs no re-vendor.
- The selected backend's define is `PRIVATE` (it affects only SoLoud's own
  compilation) and its source file is added conditionally.
- `PRIVATE` include dir `${CMAKE_CURRENT_SOURCE_DIR}/soloud`, per §2.1.

### 5.4 stb

Vendored into `libs/stb/stb/`, and the list that drives the generated targets:

| header | impl define |
|---|---|
| `stb_image.h` | `STB_IMAGE_IMPLEMENTATION` |
| `stb_image_write.h` | `STB_IMAGE_WRITE_IMPLEMENTATION` |
| `stb_truetype.h` | `STB_TRUETYPE_IMPLEMENTATION` |
| `stb_rect_pack.h` | `STB_RECT_PACK_IMPLEMENTATION` |
| `stb_ds.h` | `STB_DS_IMPLEMENTATION` |
| `stb_sprintf.h` | `STB_SPRINTF_IMPLEMENTATION` |
| `stb_perlin.h` | `STB_PERLIN_IMPLEMENTATION` |
| `stb_easy_font.h` | `STB_EASY_FONT_IMPLEMENTATION` |

`stb_vorbis` is the exception: upstream ships it as `stb_vorbis.c`, not a
header. It is vendored as-is and compiled directly as the target's source. A
consumer includes it upstream-style:
`#define STB_VORBIS_HEADER_ONLY` then `#include <stb/stb_vorbis.c>`. The README
must say so, because it is the one target whose usage is not
`#include <stb/x.h>`.

## 6. CMake helpers

`cmake/GameLibLibrary.cmake` provides three functions. They handle only the
*uniform* parts; anything platform- or config-varying stays as plain CMake in
the library's own `CMakeLists.txt`, where a reader looks for it.

```cmake
gamelib_add_library(
    NAME    sokol_app              # -> target gamelib_sokol_app + alias gamelib::sokol_app
    SOURCES src/sokol_app.c
    [INCLUDE_ROOT <dir>]           # default: CMAKE_CURRENT_SOURCE_DIR
    [PRIVATE_INCLUDES <dir>...]
)
```

Creates a `STATIC` library, sets `target_include_directories(<t> PUBLIC
<INCLUDE_ROOT>)`, adds the namespaced alias, and records the name for a
configure-time summary. The caller then applies ordinary `target_link_libraries`
/ `target_compile_definitions` / `target_compile_options` to `gamelib_<name>`.

```cmake
gamelib_add_header_library(
    NAME        stb_image
    HEADER      stb/stb_image.h
    IMPL_DEFINE STB_IMAGE_IMPLEMENTATION
    [LANGUAGE   C]                 # default C
)
```

Generates a TU from `cmake/single_header_impl.c.in`:

```c
#define @GAMELIB_IMPL_DEFINE@
#include <@GAMELIB_IMPL_HEADER@>
```

then calls `gamelib_add_library()`. This is what turns eight stb targets, plus
`sokol_log` and `sokol_time`, into single-line list entries.

```cmake
gamelib_add_example(NAME clear SOURCES clear.c LIBS gamelib::sokol_app)
```

Config and platform variation uses generator expressions
(`$<PLATFORM_ID:Linux>`, `$<CONFIG:Debug>`) rather than `if()` blocks, following
imgui-react-runtime's `imgui-runtime` target.

The root `CMakeLists.txt` prints a summary of enabled libraries, their pinned
commits, and the resolved backends.

## 7. Vendoring and updates

`tools/vendor.toml` is the single source of truth:

```toml
[sokol]
url     = "https://github.com/floooh/sokol"
commit  = "4dc4532ee402b71c374100b1eb0a7ce7286f7896"
license = "LICENSE"
copy = [
  { from = "sokol_app.h",        to = "sokol/" },
  { from = "sokol_gfx.h",        to = "sokol/" },
  { from = "sokol_glue.h",       to = "sokol/" },
  { from = "sokol_log.h",        to = "sokol/" },
  { from = "sokol_time.h",       to = "sokol/" },
  { from = "sokol_audio.h",      to = "sokol/" },
  { from = "util/sokol_imgui.h", to = "sokol/" },
]
```

Files are listed **explicitly rather than by glob**, so the manifest documents
exactly which upstream files are in the tree. Adding a sokol utility header is a
manifest line plus a re-vendor.

`tools/vendor.py` (Python 3.11+, `tomllib` from the standard library, no
third-party dependencies):

- `list` — pinned versions at a glance
- `update <lib> [--commit SHA]` — shallow-clone to a temp dir, **wipe** the
  destination directories, re-copy the mapped paths, rewrite `VERSION`, print a
  diffstat
- `check` — assert every `libs/*/VERSION` matches the manifest; run in CI

`libs/<name>/VERSION` is generated and marked as such in its own text. It is
redundant with the manifest deliberately: someone reading `libs/sokol/` should
see provenance without hunting for a tool. `vendor.py check` is what keeps the
redundancy honest.

Initial pins (upstream HEAD as of 2026-09-07):

| library | commit |
|---|---|
| sokol | `4dc4532ee402b71c374100b1eb0a7ce7286f7896` |
| imgui | `334f484892a1fa881d2a927c2aff222c15458b8f` |
| stb | `2c980bb59875b0d32144a71867fbdebb2f77cd20` |
| soloud | `e82fd32c1f62183922f08c14c814a02b58db1873` |

## 8. Examples, CI, and acceptance criteria

Examples are gated on `if(PROJECT_IS_TOP_LEVEL)` so a consumer never builds
them. Each is ~5 lines via `gamelib_add_example()`, and each doubles as the
build smoke test for its targets.

| example | exercises |
|---|---|
| `clear` | `sokol_app` + `sokol_gfx` + `sokol_time` — window, clear colour |
| `imgui` | + `sokol_imgui` + `imgui` — the ImGui demo window |
| `beep` | `sokol_audio` — a generated tone |
| `soloud` | `soloud` — an sfxr-generated sound, no asset file needed |
| `image` | `stb_image` + `sokol_gfx` — decode an embedded PNG to a texture |

CI (GitHub Actions): ubuntu-latest, macos-latest, windows-latest, each building
everything; plus `vendor.py check`; plus a **headless job** in a container with
no X11 development packages that configures with
`GAMELIB_SOKOL_BACKEND=dummy` and builds a consumer linking only
`gamelib::sokol_gfx`. Windowed examples are built, not run — `sokol_app` needs a
display.

### Acceptance criteria

1. Top-level `cmake -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build`
   succeeds on Linux, macOS and Windows; all five examples build.
2. A scratch consumer that does `add_subdirectory(game-lib EXCLUDE_FROM_ALL)`
   and links **only** `gamelib::stb_image` builds, and the build tree contains
   **no** sokol, imgui or soloud object files.
3. The headless CI job of §8 builds and links with no X11 present.
4. `set(GAMELIB_SOLOUD OFF)` before `add_subdirectory` configures cleanly and
   `libs/soloud/CMakeLists.txt` is never parsed (observable in the summary).
5. `tools/vendor.py check` exits 0.
6. A test consumer captures `CMAKE_CXX_STANDARD`, `CMAKE_C_STANDARD`,
   `CMAKE_EXECUTABLE_SUFFIX` and `get_directory_property(... INCLUDE_DIRECTORIES)`
   immediately before and after `add_subdirectory(game-lib)` and
   `message(FATAL_ERROR)`s on any difference — the mechanical form of §3.3.

## 9. Explicitly out of scope

- `install()` / `export()` / `find_package` support. Submodule +
  `add_subdirectory` is the contract; `FetchContent` works off the same
  mechanism for free. Add it when someone actually needs it.
- Any original runtime code (see §1).
- sokol-shdc or any shader compilation pipeline.
- Android, iOS, MinGW.
- cimgui, sokol_gl.
- Additional sokol utility headers — `sokol_debugtext`, `sokol_shape`,
  `sokol_color`, `sokol_fontstash`, `sokol_gfx_imgui`, `sokol_fetch`,
  `sokol_args`. Each is later a manifest line plus one
  `gamelib_add_header_library()` call; demonstrating that cheapness is part of
  the point of the structure.
