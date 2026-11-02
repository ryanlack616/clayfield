#version 330 core
uniform sampler2D source_image;
uniform sampler2D blurred_image;
uniform int filter_mode;
uniform int radius;
uniform float weights[61];
uniform float sharpen_amount;
uniform bool threshold_enabled;
uniform float threshold_value;
layout(location = 0) out float result;

int reflect101(int value, int size) {
    if (size <= 1) return 0;
    int period = 2 * (size - 1);
    int position = abs(value) % period;
    return position < size ? position : period - position;
}

void main() {
    ivec2 p = ivec2(gl_FragCoord.xy);
    if (filter_mode < 2) {
        ivec2 size = textureSize(source_image, 0);
        float value = texelFetch(source_image, p, 0).r * weights[0];
        for (int i = 1; i <= 60; ++i) {
            if (i > radius) break;
            ivec2 left = p;
            ivec2 right = p;
            if (filter_mode == 0) {
                left.x = reflect101(p.x - i, size.x);
                right.x = reflect101(p.x + i, size.x);
            } else {
                left.y = reflect101(p.y - i, size.y);
                right.y = reflect101(p.y + i, size.y);
            }
            value += weights[i] * (texelFetch(source_image, left, 0).r + texelFetch(source_image, right, 0).r);
        }
        result = value;
    } else {
        float value = texelFetch(source_image, p, 0).r;
        float blurred = texelFetch(blurred_image, p, 0).r;
        value = clamp(value + sharpen_amount * (value - blurred), 0.0, 1.0);
        result = threshold_enabled ? (value >= threshold_value ? 1.0 : 0.0) : value;
    }
}
