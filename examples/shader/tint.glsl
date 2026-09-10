/* Included by triangle.glsl via sokol-shdc's filesystem @include, so that
   shader_incremental in tools/run_tests.py can exercise the DEPFILE edge:
   editing a file the shader @includes (not the shader itself) must also
   regenerate the generated header. */
vec4 tint(vec4 c) {
    return c;
}
