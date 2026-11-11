"""OpenGL 3.3 image preview; CPU processing remains authoritative for export."""

from pathlib import Path

import cv2
import numpy as np
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader

from clayfield.image.curves import curve_lut


def supports_gpu_adjustments(settings: dict) -> bool:
    """Return whether settings fit the GPU pipeline's supported ranges."""
    black = float(settings.get("Black point", 0.0))
    white = float(settings.get("White point", 1.0))
    output_black = float(settings.get("Output black", 0.0))
    output_white = float(settings.get("Output white", 1.0))
    return (
        0 <= float(settings.get("Blur", 0.0)) <= 20
        and 0 <= float(settings.get("Sharpen", 0.0)) <= 5
        and 0 <= black < white <= 1
        and 0 <= output_black <= output_white <= 1
        and float(settings.get("Gamma", 1.0)) > 0
    )


class GpuImagePipeline:
    """Run tonal adjustments in an R32F framebuffer on the current GL context."""

    def __init__(self) -> None:
        resources = Path(__file__).resolve().parents[1] / "resources"
        self.program = compileProgram(
            compileShader((resources / "image_process.vert").read_text(), GL_VERTEX_SHADER),
            compileShader((resources / "image_process.frag").read_text(), GL_FRAGMENT_SHADER),
        )
        self.filter_program = compileProgram(
            compileShader((resources / "image_process.vert").read_text(), GL_VERTEX_SHADER),
            compileShader((resources / "image_filter.frag").read_text(), GL_FRAGMENT_SHADER),
        )
        self.vao = glGenVertexArrays(1)
        self.framebuffer = glGenFramebuffers(1)
        self.source, self.lut, self.output, self.scratch, self.scratch2 = glGenTextures(5)
        self._source_image = None
        self._dimensions = None

    def process(self, image: np.ndarray, settings: dict, points: list, *, readback: bool = True):
        if not supports_gpu_adjustments(settings):
            raise ValueError("These adjustments require the CPU pipeline")
        image = np.ascontiguousarray(image, dtype=np.float32)
        if image.ndim != 2 or not np.isfinite(image).all():
            raise ValueError("GPU image must contain finite 2D data")
        rows, columns = image.shape
        if min(rows, columns) < 1 or max(rows, columns) > int(glGetIntegerv(GL_MAX_TEXTURE_SIZE)):
            raise ValueError("GPU image dimensions exceed the supported texture size")
        lut = np.ascontiguousarray(curve_lut(points, interpolation=str(settings.get("Curve interpolation", "linear"))))
        previous_fbo = int(glGetIntegerv(GL_FRAMEBUFFER_BINDING))
        previous_viewport = tuple(int(v) for v in glGetIntegerv(GL_VIEWPORT))
        depth_enabled = bool(glIsEnabled(GL_DEPTH_TEST))
        previous_polygon_mode = int(glGetIntegerv(GL_POLYGON_MODE)[0])
        try:
            glDisable(GL_DEPTH_TEST)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glBindVertexArray(self.vao)
            glUseProgram(self.program)
            for unit, texture, data, width, height, uniform in (
                (0, self.source, image, columns, rows, "source_image"),
                (1, self.lut, lut, 4096, 1, "curve_lut"),
            ):
                glActiveTexture(GL_TEXTURE0 + unit)
                glBindTexture(GL_TEXTURE_2D, texture)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
                if texture != self.source or self._source_image is not image:
                    glTexImage2D(GL_TEXTURE_2D, 0, GL_R32F, width, height, 0, GL_RED, GL_FLOAT, data)
                glUniform1i(glGetUniformLocation(self.program, uniform), unit)
            self._source_image = image
            if self._dimensions != (columns, rows):
                for texture in (self.output, self.scratch, self.scratch2):
                    glActiveTexture(GL_TEXTURE2)
                    glBindTexture(GL_TEXTURE_2D, texture)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
                    glTexImage2D(GL_TEXTURE_2D, 0, GL_R32F, columns, rows, 0, GL_RED, GL_FLOAT, None)
                self._dimensions = (columns, rows)
            glBindFramebuffer(GL_FRAMEBUFFER, self.framebuffer)
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.output, 0)
            if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
                raise RuntimeError("GPU image-processing framebuffer is incomplete")
            glViewport(0, 0, columns, rows)
            for uniform, key, default in (
                ("black_point", "Black point", 0.0),
                ("white_point", "White point", 1.0),
                ("gamma_value", "Gamma", 1.0),
                ("output_black", "Output black", 0.0),
                ("output_white", "Output white", 1.0),
                ("brightness", "Brightness", 0.0),
                ("contrast", "Contrast", 1.0),
                ("threshold_value", "Threshold", 0.5),
            ):
                glUniform1f(glGetUniformLocation(self.program, uniform), float(settings.get(key, default)))
            blur = float(settings.get("Blur", 0))
            sharp = float(settings.get("Sharpen", 0))
            threshold_enabled = bool(settings.get("threshold_enabled", False))
            for uniform, key in (("inverted", "inverted"), ("threshold_enabled", "threshold_enabled")):
                enabled = bool(settings.get(key, False)) and (uniform != "threshold_enabled" or not (blur or sharp))
                glUniform1i(glGetUniformLocation(self.program, uniform), int(enabled))
            glDrawArrays(GL_TRIANGLES, 0, 3)
            result_texture = self.output
            if blur:
                kernel = max(3, int(round(blur * 6)) | 1)
                self._blur(self.output, self.scratch, 0, kernel, blur)
                self._blur(self.scratch, self.output, 1, kernel, blur)
            if sharp:
                self._blur(self.output, self.scratch, 0, 9, 1.0)
                self._blur(self.scratch, self.scratch2, 1, 9, 1.0)
            if sharp or (blur and threshold_enabled):
                self._finish(
                    self.output,
                    self.scratch2 if sharp else self.output,
                    self.scratch,
                    sharp,
                    threshold_enabled,
                    float(settings.get("Threshold", 0.5)),
                )
                result_texture = self.scratch
            if not readback:
                return result_texture
            result = np.empty((rows, columns), dtype=np.float32)
            glReadPixels(0, 0, columns, rows, GL_RED, GL_FLOAT, result)
            return result
        finally:
            glBindFramebuffer(GL_FRAMEBUFFER, previous_fbo)
            glViewport(*previous_viewport)
            glBindVertexArray(0)
            glPolygonMode(GL_FRONT_AND_BACK, previous_polygon_mode)
            if depth_enabled:
                glEnable(GL_DEPTH_TEST)

    def _blur(self, source, destination, direction, kernel_size, sigma):
        glUseProgram(self.filter_program)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, source)
        glUniform1i(glGetUniformLocation(self.filter_program, "source_image"), 0)
        glUniform1i(glGetUniformLocation(self.filter_program, "filter_mode"), direction)
        radius = kernel_size // 2
        glUniform1i(glGetUniformLocation(self.filter_program, "radius"), radius)
        kernel = cv2.getGaussianKernel(kernel_size, sigma, cv2.CV_32F).ravel()
        weights = np.zeros(61, dtype=np.float32)
        weights[: radius + 1] = kernel[radius:]
        glUniform1fv(glGetUniformLocation(self.filter_program, "weights"), len(weights), weights)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, destination, 0)
        glDrawArrays(GL_TRIANGLES, 0, 3)

    def _finish(self, source, blurred, destination, amount, enabled, cutoff):
        glUseProgram(self.filter_program)
        for unit, texture, uniform in ((0, source, "source_image"), (1, blurred, "blurred_image")):
            glActiveTexture(GL_TEXTURE0 + unit)
            glBindTexture(GL_TEXTURE_2D, texture)
            glUniform1i(glGetUniformLocation(self.filter_program, uniform), unit)
        glUniform1i(glGetUniformLocation(self.filter_program, "filter_mode"), 2)
        glUniform1f(glGetUniformLocation(self.filter_program, "sharpen_amount"), amount)
        glUniform1i(glGetUniformLocation(self.filter_program, "threshold_enabled"), int(enabled))
        glUniform1f(glGetUniformLocation(self.filter_program, "threshold_value"), cutoff)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, destination, 0)
        glDrawArrays(GL_TRIANGLES, 0, 3)

    def close(self) -> None:
        glDeleteTextures([self.source, self.lut, self.output, self.scratch, self.scratch2])
        glDeleteFramebuffers(1, [self.framebuffer])
        glDeleteVertexArrays(1, [self.vao])
        glDeleteProgram(self.program)
        glDeleteProgram(self.filter_program)
