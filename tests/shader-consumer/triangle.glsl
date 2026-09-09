@vs vs
in vec4 position;
out vec4 color;
void main() {
    gl_Position = position;
    color = position;
}
@end

@fs fs
in vec4 color;
out vec4 frag_color;
void main() {
    frag_color = color;
}
@end

@program triangle vs fs
