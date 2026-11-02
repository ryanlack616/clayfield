#version 330 core
layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
layout(location = 2) in vec2 texcoord;
uniform mat4 projection;
uniform mat4 view;
uniform mat4 model;
uniform sampler2D height_texture;
uniform bool gpu_displacement;
out vec3 surface_normal;
void main() {
    vec3 displaced = position;
    vec3 computed_normal = normal;
    if (gpu_displacement) {
        displaced.y = texture(height_texture, texcoord).r;
        float left = textureOffset(height_texture, texcoord, ivec2(-1, 0)).r;
        float right = textureOffset(height_texture, texcoord, ivec2(1, 0)).r;
        float down = textureOffset(height_texture, texcoord, ivec2(0, -1)).r;
        float up = textureOffset(height_texture, texcoord, ivec2(0, 1)).r;
        computed_normal = normalize(vec3(left - right, 2.0, down - up));
    }
    surface_normal = mat3(model) * computed_normal;
    gl_Position = projection * view * model * vec4(displaced, 1.0);
}
