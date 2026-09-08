# game-lib — design

Date: 2026-09-07
Revised: 2026-09-08, after an external review (OpenAI Codex) raised 14 findings,
all of which were independently verified and acted on. See §10.
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
| [miniaudio](https://github.com/mackron/miniaudio) | Unlicense *or* MIT-0 | `miniaudio.h` (one header) |
| [stb](https://github.com/nothings/stb) | MIT / public domain | 8 headers + `stb_vorbis.c`, listed in §5.4 |

Deliberately excluded: **cimgui** (needed only to call ImGui from C or to bind
an FFI; our sokol_imgui bridge TU is C++, so plain Dear ImGui suffices),
**sokol_gl**, and **SoLoud** (see §5.3 — miniaudio replaced it).

Platforms: Linux, macOS, Windows, Emscripten. Not Android, not iOS.

## 2. Repository layout

```
game-lib/
  CMakeLists.txt              cmake_minimum_required + project + conditional
                              enable_language(CXX) (§6.1), option gates,
                              add_subdirectory(libs), examples, summary
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
      sokol/                  VENDOR-OWNED: verbatim upstream headers
      src/                    ours: the impl TUs
    imgui/
      CMakeLists.txt  VERSION  LICENSE
      imgui/                  VENDOR-OWNED: upstream headers and .cpp together
    miniaudio/
      CMakeLists.txt  VERSION  LICENSE
      miniaudio/              VENDOR-OWNED: miniaudio.h
      src/                    ours: the impl TU
    stb/
      CMakeLists.txt  VERSION  LICENSE
      stb/                    VENDOR-OWNED: verbatim upstream headers
  examples/
    CMakeLists.txt
    clear/  imgui/  beep/  audio/  image/
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
   `<imgui/imgui.h>`, `<miniaudio/miniaudio.h>`, `<stb/stb_image.h>`. A pack that
   dumps thirty headers into the consumer's global include space is antisocial;
   this makes the origin of every header obvious at the use site.
2. **Upstream files are never edited or renamed.** Upstream's own sibling
   includes (`imgui.cpp` → `"imgui.h"`, `imgui.h` → `"imconfig.h"`) resolve by
   quote-relative lookup because those files stay in one directory together.
3. **Wholesale replacement on update.** `vendor.py` can `rm -rf libs/sokol/sokol`
   and re-copy, with no risk of leaving a deleted upstream file behind.

**`libs/<name>/<name>/` is the only subtree `vendor.py` deletes and re-creates**,
for every library without exception. `libs/<name>/src/` then means one thing
everywhere in the repo: code we wrote. Without that rule the same path could be
vendor-owned for one library and hand-written for another, and a wrong path in
`vendor.py`'s wipe step would silently delete our own impl TUs.

`vendor.py` does write three things *outside* that subtree, but only ever by
rewriting a specific file, never by deleting a directory: `tools/vendor.toml`,
`libs/<name>/VERSION`, and `libs/<name>/LICENSE` (copied from upstream). Nothing
else in the repository is machine-written.

This is the `include/<lib>/` refinement identified in
[apple2tc.md §6](../../../apple2tc.md) — present in neither surveyed repo —
without the file-relocation cost that made it awkward there.

**No library needs a PRIVATE include directory.** Every vendored library here is
either header-only or header-plus-our-own-TU, and our TUs use the
`<name/header.h>` form that the PUBLIC root already provides. (This was not true
of an earlier draft that vendored SoLoud, whose upstream `.cpp` files include
`"soloud.h"` bare from nested subdirectories; replacing it with miniaudio
removed the only case.)

**A standing caution, since it cost a whole finding once.** A PRIVATE include
directory hides a *header path*; it does not isolate a *linker symbol*. Before
adding any library that bundles its own copy of another — audio libraries
routinely bundle `stb_vorbis` and the `dr_libs` — check whether the pack would
then define the same symbols twice. Two copies of one C library in two archives
is at best a duplicate-symbol error and at worst a silent mis-resolution, which
is what §5.3 records about the SoLoud that used to be here.

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

- `EXCLUDE_FROM_ALL` on the `add_subdirectory` keeps game-lib's targets out of
  **the consumer's default build target**. That is the whole of the promise. It
  is *not* "nothing compiles unless linked": an explicitly requested target
  (`cmake --build . --target gamelib_miniaudio`) still builds, an inter-target
  dependency still builds, and the subdirectory is still **processed at
  configure time** regardless. In practice a consumer who never links miniaudio
  never compiles it, but the guarantee is the narrow one.
- Because configure-time processing always happens, **no library's CMakeLists
  may perform a configure-time check that fails when its own system
  dependencies are absent.** Specifically: no `find_package(... REQUIRED)` for
  anything a consumer might not have selected, and no unconditional use of a
  `<Pkg>_LIBRARIES` value that may be `<Pkg>-NOTFOUND` — a NOTFOUND value baked
  into an unused target's link interface still fails generation. Optional
  discovery must guard its own use. Criterion 3 depends on this.
- Per-library options default `ON` and exist only so a consumer can stop a
  library's CMake being parsed at all:
  `GAMELIB_SOKOL`, `GAMELIB_IMGUI`, `GAMELIB_MINIAUDIO`, `GAMELIB_STB`.
- **Declaration is dependency-aware.** A target is declared only if everything
  it needs was declared: `GAMELIB_IMGUI=OFF` means `gamelib_sokol_imgui` is not
  declared at all, and an example is declared only when every target it needs
  exists. game-lib prints a `message(STATUS)` naming each target it did not
  declare and why. There is no separate "request this target anyway" mechanism:
  a consumer that links an undeclared target gets CMake's own missing-target
  error at generation time, and the STATUS lines are what make that error easy
  to diagnose.
- Configuration options, where a library genuinely has a choice:
  - `GAMELIB_SOKOL_BACKEND` = `auto` (default) | `glcore` | `gles3` | `metal` |
    `d3d11` | `dummy`. `auto` resolves to metal on macOS, d3d11 on Windows,
    glcore on Linux, gles3 on Emscripten.
  - `GAMELIB_MINIAUDIO_RUNTIME_LINKING` = `OFF` (default) | `ON`. macOS only;
    see §5.3. `OFF` compiles with `MA_NO_RUNTIME_LINKING` and links the three
    CoreAudio frameworks explicitly, which is what an app that will be notarized
    needs.

  There is deliberately **no audio backend option**. miniaudio compiles in every
  backend its platform offers and selects at run time, so the SoLoud-style
  compile-time backend choice has no equivalent and needs none.

#### Supported backend x platform

| backend | Linux | macOS | Windows | Emscripten | declares `sokol_app`? |
|---|---|---|---|---|---|
| `glcore` | yes (GLX) | yes | yes | — | yes |
| `gles3` | yes (EGL) | — | — | yes | yes |
| `metal` | — | yes | — | — | yes |
| `d3d11` | — | — | yes | — | yes |
| `dummy` | yes | yes | yes | yes | **no** |

`dummy` is a **gfx-only** backend. `sokol_app.h` rejects it outright — its
platform blocks `#error` unless one of `SOKOL_METAL` / `SOKOL_GLCORE` /
`SOKOL_D3D11` / `SOKOL_GLES3` / `SOKOL_WGPU` / `SOKOL_NOAPI` is defined. So with
`GAMELIB_SOKOL_BACKEND=dummy`, `gamelib_sokol_app`, `gamelib_sokol_imgui` and
every windowed example are **not declared**. That is the configuration
criterion 3 exercises.

### 3.3 The rule: game-lib adds, it never changes

Stated precisely, because the loose version ("never mutates global state") is
both false and impossible — `project()`, cache options and package discovery are
all deliberate parts of this design.

**game-lib may:** declare targets, all of them namespaced `gamelib_*` /
`gamelib::*`; create cache entries whose names begin with `GAMELIB_`; call
`project()` and `enable_language()`; and cause CMake's own discovery modules to
create their standard cache entries.

**game-lib may not:** change the value of any cache entry that existed before
`add_subdirectory`; write to the parent scope (`set(... PARENT_SCOPE)`); or
declare a target whose name is not namespaced.

**Prohibited commands anywhere in this repo**, as hygiene rather than because
they reach the consumer: `include_directories()`, `add_definitions()`,
`link_libraries()`, and `set()` of `CMAKE_CXX_STANDARD`, `CMAKE_C_STANDARD`,
`CMAKE_*_FLAGS` or `CMAKE_EXECUTABLE_SUFFIX`.

Note carefully what these *do* and do not do. An ordinary `set()` is scoped to
the current directory and its descendants; only `PARENT_SCOPE` reaches upward.
So `imgui-react-runtime`'s `set(CMAKE_EXECUTABLE_SUFFIX ".html")` in
`external/sokol/CMakeLists.txt` does **not** rename a consumer's binaries, and
does not even reach its own sibling `examples/`. The reason to ban these
commands here is narrower: inside game-lib they still affect that library's
directory and everything beneath it, which makes one library's CMakeLists able
to silently change how its own subdirectories build. Each library must be
readable on its own.

Everything is expressed with `target_*` commands. Language requirements become
`target_compile_features(gamelib_imgui PUBLIC cxx_std_11)`.

This rule is testable; see §8, criterion 6.

## 4. Target catalogue

| target | sources | depends on | system links |
|---|---|---|---|
| `gamelib::sokol_gfx` | `src/sokol_gfx.c` | — | **its own backend libs** — see §5.1 |
| `gamelib::sokol_app` | `src/sokol_app.c` (app + glue) | `sokol_gfx` | *additional* windowing libs — see §5.1 |
| `gamelib::sokol_log` | generated TU (`SOKOL_LOG_IMPL`) | — | none |
| `gamelib::sokol_time` | generated TU (`SOKOL_TIME_IMPL`) | — | none |
| `gamelib::sokol_audio` | `src/sokol_audio.c` | — | Linux `asound` + `-pthread`; macOS `AudioToolbox`; Windows/MSVC none |
| `gamelib::sokol_imgui` | `src/sokol_imgui.cc` (**C++**) | `sokol_app`, `sokol_gfx`, `imgui` | none |
| `gamelib::imgui` | 5 upstream `.cpp` | — | none |
| `gamelib::miniaudio` | `src/miniaudio.c` | — | Linux `dl m` + `-pthread`; macOS see §5.3; Windows none |
| `gamelib::stb_image` | generated TU | — | `m` (§5.4) |
| `gamelib::stb_image_write` | generated TU | — | `m` |
| `gamelib::stb_truetype` | generated TU | — | `m` |
| `gamelib::stb_rect_pack` | generated TU | — | `m` |
| `gamelib::stb_ds` | generated TU | — | `m` |
| `gamelib::stb_sprintf` | generated TU | — | `m` |
| `gamelib::stb_perlin` | generated TU | — | `m` |
| `gamelib::stb_easy_font` | generated TU | — | `m` |
| `gamelib::stb_vorbis` | `stb/stb_vorbis.c` directly | — | `m` |

**Every target declares the libraries its own implementation needs**, not the
libraries its typical companions happen to provide. `sokol_gfx.h` has a "Link
with the following system libraries" section of its own, prefaced "note that
sokol_app.h has *additional* linker requirements" — so gfx carries the backend
libraries and app carries only the windowing ones on top. Getting this wrong is
invisible in a full app build and fatal for the single-target consumer the pack
exists to serve.

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

### 4.2 Why nine separate stb targets

Each stb header compiles to its own TU and gets its own target, so a consumer
that wants `stb_image` does not compile `stb_truetype`. Eight of the nine are
*generated by a loop* over the list in §5.4 — eight targets from eight list
entries, not eight hand-written CMake blocks. `stb_vorbis` is the exception:
upstream ships it as `stb_vorbis.c`, not a header, so it is compiled directly.

The alternative considered and rejected: one `gamelib::stb` static archive
containing nine objects, relying on the linker to pull only referenced members.
That yields the same binary, but still *compiles* all nine whenever any is
linked.

`gamelib::stb_vorbis` is the one target whose usage is not
`#include <stb/x.h>`. A consumer includes it upstream-style:

```c
#define STB_VORBIS_HEADER_ONLY
#include <stb/stb_vorbis.c>
```

It pairs directly with `gamelib::miniaudio`, whose built-in decoders cover WAV,
MP3 and FLAC but not Ogg Vorbis. The README must say both things.

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

#### System libraries

Split between the two targets exactly as the two headers document their own
requirements. `sokol_gfx.h` carries the **rendering backend**; `sokol_app.h`
adds the **windowing** libraries on top.

`gamelib_sokol_gfx` — from `sokol_gfx.h`'s "Link with the following system
libraries" section:

| platform / backend | links |
|---|---|
| macOS + metal | `Metal` |
| macOS + glcore | `OpenGL` |
| Linux + glcore (GLX) | `GL` |
| Linux + gles3 (EGL) | `GLESv2`, `EGL` |
| Windows + d3d11, MSVC/Clang | nothing (`#pragma comment`) |
| Windows + glcore | nothing (sokol_gfx ships its own GL loader on Windows) |
| Emscripten | `target_link_options(... INTERFACE -sUSE_WEBGL2=1)` |
| `dummy`, any platform | nothing |

`gamelib_sokol_app` — the *additional* requirements from `sokol_app.h`:

| platform | links |
|---|---|
| Linux, all backends | `X11 Xi Xcursor dl m` + the `-pthread` flag |
| macOS, all backends | `AppKit`, `QuartzCore` |
| Windows, MSVC/Clang | nothing (`#pragma comment`) |

Two subtleties in that table:

- **GLX versus EGL on Linux.** `sokol_app.h` says "GLX is default, set
  SOKOL_FORCE_EGL to override", and its Linux GLES3 path selects EGL
  unconditionally. game-lib never sets `SOKOL_FORCE_EGL`, so glcore means GLX
  (`GL` alone) and gles3 means EGL (`GLESv2` **and** `EGL`).
- **The `-pthread` flag must be literal.** Do *not* rely on
  `THREADS_PREFER_PTHREAD_FLAG` + `Threads::Threads`: FindThreads documents that
  the preference "has no effect if the system libraries provide the thread
  functions", and it checks libc *before* checking the flag. On glibc 2.34+
  pthread lives in libc, so `Threads::Threads` would carry no flag at all, while
  upstream issue #376 requires it as both a compile and a link option. Use
  `target_compile_options(<t> PUBLIC $<$<PLATFORM_ID:Linux>:-pthread>)` and the
  matching `target_link_options`.

`sokol_audio.h` (`gamelib_sokol_audio`): Linux `asound` **plus the `-pthread`
flag** — its ALSA backend calls `pthread_create()` and `pthread_join()`
directly; macOS `AudioToolbox`; Windows/MSVC nothing.

#### Objective-C on Apple

`sokol_app.h` states the implementation **must be compiled as Objective-C** on
macOS. Rule: on Apple, compile **every** sokol impl TU as Objective-C —
`-x objective-c` for the `.c` TUs and `-x objective-c++` for `sokol_imgui.cc` —
via `target_compile_options(... PRIVATE ...)`, rather than maintaining duplicate
`.m` files as apple2tc does. Applied uniformly on purpose: Objective-C is a
superset of C, so it is harmless for a TU that does not need it, and a per-file
rule would silently break the day a backend change makes another TU touch a
platform API.

(Note `AppKit`, not the older `Cocoa` both surveyed repos use. MinGW is out of
scope for the initial version.)

#### Consumer-visible include ordering

`sokol_glue.h` `#error`s with "Please include sokol_gfx.h before sokol_glue.h"
at the *declaration* level, and demands `sokol_app.h` before its
*implementation*. A consumer including `<sokol/sokol_glue.h>` must therefore
include `<sokol/sokol_gfx.h>` first. The README must say so.

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

### 5.3 miniaudio

Vendored as a single file, `libs/miniaudio/miniaudio/miniaudio.h`, plus our
`libs/miniaudio/src/miniaudio.c`:

```c
#define MINIAUDIO_IMPLEMENTATION
#include <miniaudio/miniaudio.h>
```

Pure C, so this target does not pull in the C++ requirement of §6.1.

**No backend option**, per §3.2: miniaudio compiles every backend its platform
offers (WASAPI, CoreAudio, ALSA, PulseAudio, JACK, sndio, Web Audio…) and
selects at run time. Nothing to configure and nothing to get wrong.

**System links**, from miniaudio's own "Building" section:

| platform | links |
|---|---|
| Linux | `dl m` + the `-pthread` flag ("You do not need any development packages") |
| Windows | nothing — "compile cleanly on all popular compilers without the need to configure any include paths nor link to any libraries" |
| macOS, default (`GAMELIB_MINIAUDIO_RUNTIME_LINKING=OFF`) | `MA_NO_RUNTIME_LINKING` + `CoreFoundation`, `CoreAudio`, `AudioToolbox` |
| macOS, `...=ON` | nothing |
| Emscripten | nothing; it emits Web Audio JavaScript directly |

Three constraints that are easy to miss and must be encoded in the CMake:

1. **The macOS default is the non-obvious one.** Left to itself miniaudio links
   frameworks at *run time*, and its documentation warns that "your application
   may not pass Apple's notarization process" as a result. A pack meant for
   shipping games should default to the notarizable configuration, so
   `GAMELIB_MINIAUDIO_RUNTIME_LINKING` defaults to `OFF` — i.e. compile with
   `MA_NO_RUNTIME_LINKING` and link the three frameworks explicitly. The option
   exists for a consumer who prefers upstream's default.
2. **Emscripten forbids a C standard flag.** miniaudio states: "You cannot use
   `-std=c*` compiler flags, nor `-ansi`. This only applies to the Emscripten
   build." So `gamelib_miniaudio` must never carry `target_compile_features(...
   c_std_*)` — or anything else that makes CMake emit `-std=`— under Emscripten.
   This is the one place the pack's own conventions have to yield to a library.
3. **Static linking only.** miniaudio "is not ABI compatible between any
   release, including bug fix releases", and recommends linking statically.
   That is already the pack's model, but it is a reason not to relax it.

Ogg Vorbis is not among miniaudio's built-in decoders (WAV, MP3 and FLAC are).
`gamelib::stb_vorbis` exists to fill that gap; see §4.2.

#### Why not SoLoud

An earlier draft of this spec vendored [SoLoud](https://github.com/jarikomppa/soloud)
instead. It was replaced on 2026-09-08, on these grounds:

- **SoLoud's default backend already *was* miniaudio** — it vendors its own copy
  of `miniaudio.h` under `src/backend/miniaudio/`. The pack was therefore
  shipping miniaudio wrapped in a second layer, rather than avoiding it.
- That layer is unmaintained: last upstream commit 2024-08-13, 122 open issues,
  against miniaudio's 2026-03-03 and 7.
- ~200 vendored files became 2. The licence became more permissive (Unlicense or
  MIT-0, versus zlib). The spatial-audio API became better: miniaudio has
  listeners, cones, doppler and attenuation models where SoLoud has basic
  panning.
- Removing SoLoud is what allowed `gamelib::stb_vorbis` back into the catalogue
  (§4.2), and stb_vorbis is exactly what miniaudio needs for Ogg.

**What was given up, honestly:** SoLoud's generated sound sources have no
miniaudio equivalent — `sfxr` (procedural retro sound effects), `speech` (a
speech synthesiser), and the chiptune sources `ay`, `monotone`, `tedsid`, `vic`,
`vizsn`. If any of those is wanted later, note that SoLoud cannot simply be
added back alongside: it would compile its own `ma_*` symbols into a second
archive, which is the same collision class described in §2.1. It would have to
be ported onto the pack's miniaudio copy.

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

Every one of these targets links `m` on Linux, macOS and Emscripten, and nothing
extra on Windows. `stb_image` alone would justify it — it calls `pow()` and
`ldexp()` in its default configuration — and applying the rule uniformly rather
than auditing each header per release is the deliberate trade. It overstates the
dependency for a header that needs no math functions; it hides no correctness
distinction. The rule is scoped to the four supported platforms and must be
revisited if a fifth is added.

`stb_vorbis.c` is vendored alongside them and compiled directly as
`gamelib::stb_vorbis`'s own source — upstream ships it as a `.c`, not a header,
so it is not part of the generated-target list above. It is the pack's Ogg
Vorbis decoder, which `gamelib::miniaudio` does not include; see §4.2 for the
consumer-side include form.

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
    [LIBS <lib>...]                # PUBLIC link libraries, genex allowed
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
    [LIBS <lib>...]                # forwarded to gamelib_add_library
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

### 6.1 The root preamble

```cmake
cmake_minimum_required(VERSION 3.21)
project(game-lib LANGUAGES C)
```

Both lines are load-bearing:

- **3.21** is the floor for `PROJECT_IS_TOP_LEVEL` (§8). It also carries
  **CMP0077 NEW**, without which §3.2's `set(GAMELIB_MINIAUDIO OFF)` before
  `add_subdirectory` silently does nothing: `option()` under the OLD behaviour
  deletes the parent's normal variable and creates a cache entry set to `ON`.
  `target_link_options` separately needs 3.13.
- **An explicit `project()` call** is required, not optional.
  `PROJECT_IS_TOP_LEVEL` is set by `project()` and otherwise *inherited from the
  parent scope* — so without this line, a consumer whose own project is
  top-level would see `PROJECT_IS_TOP_LEVEL` true inside game-lib and build all
  of game-lib's examples.

**`LANGUAGES C`, with CXX enabled on demand.** `project(... LANGUAGES C CXX)`
would force every consumer through C++ compiler detection, including one that
selects only C libraries; `EXCLUDE_FROM_ALL` cannot suppress that. So game-lib
declares C only, and calls `enable_language(CXX)` **from its own root
CMakeLists, before `add_subdirectory(libs)` and `add_subdirectory(examples)`**,
whenever any C++ library is enabled. There are only two: `imgui` and
`sokol_imgui`. sokol, miniaudio and stb are all pure C.

The placement is not free choice. CMake requires a language to be enabled in the
highest directory common to every target using it, and game-lib's C++ *examples*
live under `examples/` while its C++ *libraries* live under `libs/` — siblings
whose only common ancestor is game-lib's root. Enabling CXX inside
`libs/CMakeLists.txt` would satisfy the libraries and leave the examples
invalid.

Note the consequence for a consumer who wants to avoid C++ compiler detection
entirely: linking only C targets does **not** achieve it, because the C++
library options default to `ON` and the decision is made at configure time. Such
a consumer must set `GAMELIB_IMGUI=OFF` explicitly — that one option is now the
whole of it, since imgui and its sokol bridge are the only C++ in the pack. The
README says so.

Two documented consequences of the nested `project()`:

- Local `PROJECT_*` variables become game-lib's; top-level identity variables
  such as `CMAKE_PROJECT_NAME` stay the parent's, which is the documented
  behaviour. A parent's `CMAKE_PROJECT_INCLUDE` / `CMAKE_PROJECT_INCLUDE_BEFORE`
  hooks also run for this nested call.
- CMake requires a language to be enabled in the highest directory common to all
  targets using it, *including through link dependencies*. **A consumer linking
  any C++ target of ours — `gamelib::imgui` or `gamelib::sokol_imgui` — must
  enable CXX in its own top-level project.** The
  README states this.

The root `CMakeLists.txt` prints a summary of enabled libraries, their pinned
commits, the resolved backends, and every target it declined to declare with the
reason (§3.2).

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

- `list` — pinned versions at a glance, and whether each is behind upstream's
  default branch
- `update <lib> --commit <SHA>` — move to that exact commit.
- `update <lib>` with no `--commit` — move to the **current HEAD of upstream's
  default branch**. This is the only command in the pack that consults "latest",
  and it is always an explicit, deliberate act: nothing in a normal build,
  configure or CI run ever contacts the network or advances a pin. A build is
  reproducible from the checkout alone.
- `update <lib> --recheck` — re-vendor the commit already in the manifest,
  without changing the pin. This is the repair operation for a tree someone has
  edited by hand; `check` (below) detects the metadata drift, `--recheck`
  restores the sources.

Both `update` forms then: fetch into a temp dir, **wipe** the destination
  directories, re-copy the mapped paths, then rewrite **both `vendor.toml` and
  `VERSION`**, and print a diffstat. Writing the manifest is not optional: it is
  the authoritative pin, so an `update --commit` that changed only `VERSION`
  would leave `check` failing immediately.
  Fetch method, since a pinned commit is usually not branch HEAD:
  `git init` + `git remote add` + `git fetch --depth 1 origin <sha>` +
  `git checkout FETCH_HEAD`, falling back to a full clone when the server
  refuses to serve an arbitrary SHA.
- `check` — assert every `libs/*/VERSION` matches the manifest; run in CI

`libs/<name>/VERSION` is generated and marked as such in its own text. It is
redundant with the manifest deliberately: someone reading `libs/sokol/` should
see provenance without hunting for a tool. `vendor.py check` is what keeps the
redundancy honest.

**Initial pins.** The table below records upstream HEAD as of 2026-09-07, the
day the design was written. It is a starting point, not a requirement: two of
the four moved within a day (sokol to `c24221dc` and imgui to `148d128f` by
2026-09-08), so the implementer should run `vendor.py update` on each library at
the start of implementation and commit whatever SHAs that produces. What matters
is that the manifest, the `VERSION` files and the vendored trees agree — which
`check` enforces — not that any particular commit was chosen.

| library | commit |
|---|---|
| sokol | `4dc4532ee402b71c374100b1eb0a7ce7286f7896` |
| imgui | `334f484892a1fa881d2a927c2aff222c15458b8f` |
| stb | `2c980bb59875b0d32144a71867fbdebb2f77cd20` |
| miniaudio | `9634bedb5b5a2ca38c1ee7108a9358a4e233f14d` |

## 8. Examples, CI, and acceptance criteria

Examples are gated on `if(PROJECT_IS_TOP_LEVEL)` so a consumer never builds
them. Each is ~5 lines via `gamelib_add_example()`, and each doubles as the
build smoke test for its targets.

| example | exercises |
|---|---|
| `clear` | `sokol_app` + `sokol_gfx` + `sokol_time` — window, clear colour |
| `imgui` | + `sokol_imgui` + `imgui` — the ImGui demo window |
| `beep` | `sokol_audio` — a generated tone |
| `audio` | `miniaudio` — decodes an embedded WAV through `ma_engine` |
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
   and links **only** `gamelib::stb_image` builds *and runs*, and the build tree
   contains **no** sokol, imgui or miniaudio object files. The consumer must
   actually **call** the decoder (`stbi_load_from_memory` on an embedded PNG),
   not merely name the target: a link-only test would not have caught the
   missing `libm` dependency.
3. The headless CI job of §8 configures, builds and links with no X11
   development packages present, using `GAMELIB_SOKOL_BACKEND=dummy` and linking
   only `gamelib::sokol_gfx`. Configuring is part of the test — §3.2 forbids a
   configure-time check that fails when an unselected library's system
   dependencies are absent.
4. `set(GAMELIB_MINIAUDIO OFF)` before `add_subdirectory` configures cleanly, and
   `libs/miniaudio/CMakeLists.txt` never appears as a trace source location under
   `cmake --trace-expand --trace-redirect=<file>`. The configure summary alone
   cannot prove this — an implementation could enter the file and return early.
5. `tools/vendor.py check` exits 0.
6. The mechanical form of §3.3, in two parts, because a directory-scoped `set()`
   is invisible to the parent and so cannot be detected by comparing the
   parent's variables:
   a. Under `--trace-expand --trace-redirect=<file>`, no prohibited command
      appears with a game-lib-owned source location. The prohibited set is
      `include_directories`, `add_definitions`, `link_libraries`, `set` of
      `CMAKE_*_FLAGS` / `CMAKE_*_STANDARD` / `CMAKE_EXECUTABLE_SUFFIX`, and
      **any `set(... PARENT_SCOPE)`** — the last covers the one way a
      directory-scoped write can escape upward. Separately, every target the
      configure creates under game-lib must be named `gamelib_*`, checked by
      walking `BUILDSYSTEM_TARGETS` on game-lib's directories.
   b. No cache entry that existed before `add_subdirectory(game-lib)` has
      changed value, and every newly created entry is one of: an entry beginning
      with `GAMELIB_`; an entry created by one of CMake's own discovery modules;
      or one of the three `project()` writes, which are **`game-lib_SOURCE_DIR`,
      `game-lib_BINARY_DIR` and `game-lib_IS_TOP_LEVEL`** (verified empirically:
      `project()` writes these as `STATIC` cache entries even for a nested
      call). Asserting the whole cache is unchanged would be wrong — §6.1's
      `project()` and §3.2's options both legitimately add entries.

## 9. Explicitly out of scope

- `install()` / `export()` / `find_package` support. Submodule +
  `add_subdirectory` is the contract; `FetchContent` works off the same
  mechanism for free. Add it when someone actually needs it.
- Any original runtime code (see §1).
- sokol-shdc or any shader compilation pipeline.
- Android, iOS, MinGW.
- cimgui, sokol_gl.
- SoLoud, and with it sfxr, the speech synthesiser and the chiptune sound
  sources; see §5.3, which also explains why it cannot simply be added back
  alongside miniaudio.
- Additional sokol utility headers — `sokol_debugtext`, `sokol_shape`,
  `sokol_color`, `sokol_fontstash`, `sokol_gfx_imgui`, `sokol_fetch`,
  `sokol_args`. Each is later a manifest line plus one
  `gamelib_add_header_library()` call; demonstrating that cheapness is part of
  the point of the structure.

## 10. Change and review record

### Audio: SoLoud replaced by miniaudio (2026-09-08)

Prompted by noticing that SoLoud's upstream had not moved since August 2024. The
finding that settled it was that SoLoud's selected backend already vendored
miniaudio, so the pack was shipping the same engine underneath an unmaintained
wrapper. Full rationale, and what was given up, in §5.3.

### Spec review

This spec was reviewed on 2026-09-08 by OpenAI Codex (codex-cli 0.153.4) acting
as an independent adversarial reviewer, with the current upstream headers
supplied as reference material. It returned 14 findings and the verdict "not
ready for implementation". Every finding was independently verified against the
sources before being acted on; none was contested. Twelve resolutions were
accepted on the first pass, two (§3.3's rule statement and §3.2's option
semantics) were returned as insufficient and revised.

A third round caught six further problems, five of which the amendments
themselves had introduced: stale SoLoud paths left behind by the move to a
single vendor-owned subtree, a vendor-ownership rule that contradicted
`vendor.py`'s own metadata writes, a backend matrix that disagreed with the link
table about Linux GLES3, SoLoud's core dependencies misattributed to its default
backend, `enable_language(CXX)` placed in `libs/` where it could not cover the
examples, and a cache whitelist that would have rejected `project()`'s own
entries. The lesson recorded for the implementer: a spec edit that moves a path
or narrows a rule has to be followed through every table that repeats it.

Three of the findings corrected outright errors of fact in the first draft, and
are recorded here because each is the kind of mistake that would otherwise be
made again:

1. **Targets did not declare their own link dependencies.** `sokol_gfx`,
   `stb_image`, `sokol_audio` and `soloud` were each credited with fewer system
   libraries than their own upstream documentation requires — invisible in a
   full application build, fatal for the single-target consumer this pack exists
   to serve. Fixed in §4, §5.1, §5.3, §5.4.
2. **PRIVATE include directories were claimed to prevent a symbol collision.**
   They do not. This is what removed `gamelib::stb_vorbis` (§4.2).
3. **A directory-scoped `set()` was claimed to reach the parent project.** It
   does not; only `PARENT_SCOPE` does. §3.3's rule survived but its
   justification and its test (§8, criterion 6) were both wrong and were
   rewritten.
