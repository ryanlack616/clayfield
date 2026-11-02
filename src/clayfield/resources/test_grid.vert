#version 330 core
layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
layout(location = 2) in vec2 texcoord;
uniform mat4 projection;
uniform mat4 view;
uniform mat4 model;
uniform sampler2D height_texture;
uniform sampler2D mapping_curve;
uniform bool gpu_displacement;
uniform vec2 sample_spacing;
uniform bool map_gpu_intensity;
uniform vec2 physical_height_bounds;
uniform float mapping_gamma;
uniform float relief_sign;
out vec3 surface_normal;
out float surface_height;
float physical_height(float sample_value) {
    if (!map_gpu_intensity) return sample_value;
    int index = int(roundEven(clamp(sample_value, 0.0, 1.0) * 4095.0));
    float mapped = texelFetch(mapping_curve, ivec2(index, 0), 0).r;
    mapped = pow(clamp(mapped, 0.0, 1.0), 1.0 / mapping_gamma);
    return relief_sign * mix(physical_height_bounds.x, physical_height_bounds.y, mapped) / 20.0;
}
void main() {
    vec3 displaced = position;
    vec3 computed_normal = normal;
    surface_height = position.y;
    if (gpu_displacement) {
        surface_height = physical_height(texture(height_texture, texcoord).r);
        displaced.y = surface_height;
        float left = physical_height(textureOffset(height_texture, texcoord, ivec2(-1, 0)).r);
        float right = physical_height(textureOffset(height_texture, texcoord, ivec2(1, 0)).r);
        float down = physical_height(textureOffset(height_texture, texcoord, ivec2(0, -1)).r);
        float up = physical_height(textureOffset(height_texture, texcoord, ivec2(0, 1)).r);
        computed_normal = normalize(vec3((left - right) / max(2.0 * sample_spacing.x, 0.000001), 1.0, (down - up) / max(2.0 * sample_spacing.y, 0.000001)));
    }
    surface_normal = mat3(model) * computed_normal;
    gl_Position = projection * view * model * vec4(displaced, 1.0);
}
