from __future__ import annotations

import cv2
import numpy
import onnxruntime

from .models import default_model_path, ensure_model_file

_GPU_DEVICE_IDS = {
    "GPU 1": "0",
    "GPU 2": "1",
    "GPU 3": "2",
    "GPU 4": "3",
}


class AIFrameGenerator:
    def __init__(
        self,
        selected_AI_model: str,
        selected_gpu: str,
        frame_gen_factor: int,
    ) -> None:
        self.selected_AI_model = selected_AI_model
        self.selected_gpu = selected_gpu
        self.frame_gen_factor = frame_gen_factor

        self.selected_AI_model_path = default_model_path(selected_AI_model)

        self.inferenceSession: onnxruntime.InferenceSession | None = None
        self.input_name: str | None = None

    def _load_inferenceSession(self) -> onnxruntime.InferenceSession:
        ensure_model_file(self.selected_AI_model_path)

        if "DmlExecutionProvider" in onnxruntime.get_available_providers():
            providers = ["DmlExecutionProvider"]
            if self.selected_gpu in _GPU_DEVICE_IDS:
                provider_options = [{"device_id": _GPU_DEVICE_IDS[self.selected_gpu]}]
            else:
                provider_options = [{"performance_preference": "high_performance"}]
        else:
            providers = ["CPUExecutionProvider"]
            provider_options = None

        sess_options = onnxruntime.SessionOptions()
        sess_options.enable_profiling = False

        return onnxruntime.InferenceSession(
            path_or_bytes=self.selected_AI_model_path,
            sess_options=sess_options,
            providers=providers,
            provider_options=provider_options,
        )

    def _ensure_session(self) -> None:
        if self.inferenceSession is None:
            self.inferenceSession = self._load_inferenceSession()
            self.input_name = self.inferenceSession.get_inputs()[0].name

    # Internal helpers

    def get_image_resolution(self, image: numpy.ndarray) -> tuple[int, int]:
        return image.shape[0], image.shape[1]

    def resize_image(self, image: numpy.ndarray, resize_factor: float) -> numpy.ndarray:
        old_height, old_width = self.get_image_resolution(image)

        new_width = int(old_width * resize_factor)
        new_height = int(old_height * resize_factor)

        new_width = new_width if new_width % 2 == 0 else new_width + 1
        new_height = new_height if new_height % 2 == 0 else new_height + 1

        if new_width == old_width and new_height == old_height:
            return image

        interpolation = cv2.INTER_LINEAR if resize_factor > 1 else cv2.INTER_AREA
        return cv2.resize(image, (new_width, new_height), interpolation=interpolation)

    # Inference

    def concatenate_images(self, image1: numpy.ndarray, image2: numpy.ndarray) -> numpy.ndarray:
        image1 = image1 / 255
        image2 = image2 / 255
        return numpy.concatenate((image1, image2), axis=2)

    def preprocess_image(self, image: numpy.ndarray) -> numpy.ndarray:
        image = numpy.transpose(image, (2, 0, 1))
        return numpy.expand_dims(image, axis=0)

    def onnxruntime_inference(self, image: numpy.ndarray) -> numpy.ndarray:
        onnx_input = {self.input_name: image}
        return self.inferenceSession.run(None, onnx_input)[0]

    def postprocess_output(self, onnx_output: numpy.ndarray) -> numpy.ndarray:
        onnx_output = numpy.squeeze(onnx_output, axis=0)
        onnx_output = numpy.clip(onnx_output, 0, 1)
        onnx_output = numpy.transpose(onnx_output, (1, 2, 0))
        return onnx_output.astype(numpy.float32)

    def de_normalize_image(self, onnx_output: numpy.ndarray, max_range: int) -> numpy.ndarray:
        if max_range == 255:
            return (onnx_output * max_range).astype(numpy.uint8)
        return (onnx_output * max_range).round().astype(numpy.float32)

    def AI_interpolation(self, image1: numpy.ndarray, image2: numpy.ndarray) -> numpy.ndarray:
        self._ensure_session()
        image = self.concatenate_images(image1, image2).astype(numpy.float32)
        image = self.preprocess_image(image)
        onnx_output = self.onnxruntime_inference(image)
        onnx_output = self.postprocess_output(onnx_output)
        return self.de_normalize_image(onnx_output, 255)

    # Public API

    def AI_orchestration(self, image1: numpy.ndarray, image2: numpy.ndarray) -> list[numpy.ndarray]:
        if self.frame_gen_factor == 2:
            image_A = self.AI_interpolation(image1, image2)
            return [image_A]

        if self.frame_gen_factor == 4:
            image_B = self.AI_interpolation(image1, image2)
            image_A = self.AI_interpolation(image1, image_B)
            image_C = self.AI_interpolation(image_B, image2)
            return [image_A, image_B, image_C]

        if self.frame_gen_factor == 8:
            image_D = self.AI_interpolation(image1, image2)
            image_B = self.AI_interpolation(image1, image_D)
            image_A = self.AI_interpolation(image1, image_B)
            image_C = self.AI_interpolation(image_B, image_D)
            image_F = self.AI_interpolation(image_D, image2)
            image_E = self.AI_interpolation(image_D, image_F)
            image_G = self.AI_interpolation(image_F, image2)
            return [image_A, image_B, image_C, image_D, image_E, image_F, image_G]

        raise ValueError(f"Unsupported frame_gen_factor: {self.frame_gen_factor}")
