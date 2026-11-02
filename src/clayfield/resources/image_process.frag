#version 330 core
uniform sampler2D source_image;
uniform sampler2D curve_lut;
uniform float black_point;
uniform float white_point;
uniform float gamma_value;
uniform float output_black;
uniform float output_white;
uniform float brightness;
uniform float contrast;
uniform bool inverted;
uniform bool threshold_enabled;
uniform float threshold_value;
layout(location = 0) out float result;
void main() {
    float value = texelFetch(source_image, ivec2(gl_FragCoord.xy), 0).r;
    if (inverted) value = 1.0 - clamp(value, 0.0, 1.0);
    value = clamp((value - black_point) / (white_point - black_point), 0.0, 1.0);
    value = output_black + pow(value, 1.0 / gamma_value) * (output_white - output_black);
    int index = int(roundEven(clamp(value, 0.0, 1.0) * 4095.0));
    value = texelFetch(curve_lut, ivec2(index, 0), 0).r;
    value = clamp((value - 0.5) * contrast + 0.5 + brightness, 0.0, 1.0);
    if (threshold_enabled) value = value >= threshold_value ? 1.0 : 0.0;
    result = value;
}
