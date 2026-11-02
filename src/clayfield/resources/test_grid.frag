#version 330 core
uniform vec3 color;
uniform bool lit_surface;
uniform bool height_coloring;
uniform float height_min;
uniform float height_max;
uniform vec3 light_direction;
uniform float ambient_strength;
in vec3 surface_normal;
in float surface_height;
out vec4 fragment_color;
void main() {
    vec3 final_color = color;
    if (height_coloring) {
        float normalized_height = clamp((surface_height - height_min) / max(0.0001, height_max - height_min), 0.0, 1.0);
        final_color = mix(vec3(0.08, 0.25, 0.85), vec3(0.9, 0.2, 0.08), normalized_height);
    }
    if (lit_surface) {
        vec3 normal = normalize(surface_normal);
        float diffuse = max(dot(normal, normalize(light_direction)), 0.0);
        final_color *= ambient_strength + (1.0 - ambient_strength) * diffuse;
    }
    fragment_color = vec4(final_color, 1.0);
}
