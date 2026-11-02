#version 330 core
uniform vec3 color;
uniform bool lit_surface;
in vec3 surface_normal;
out vec4 fragment_color;
void main() {
    vec3 final_color = color;
    if (lit_surface) {
        vec3 normal = normalize(surface_normal);
        vec3 light_direction = normalize(vec3(-0.45, 0.85, 0.35));
        float diffuse = max(dot(normal, light_direction), 0.0);
        final_color *= 0.25 + 0.75 * diffuse;
    }
    fragment_color = vec4(final_color, 1.0);
}
