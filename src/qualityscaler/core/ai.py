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


class AIUpscaler:
    def __init__(
        self,
        selected_AI_model: str,
        selected_gpu: str,
        input_resize_factor: float,
        tiles_resolution: int,
    ) -> None:
        self.selected_AI_model = selected_AI_model
        self.selected_gpu = selected_gpu
        self.input_resize_factor = input_resize_factor
        self.tiles_resolution = tiles_resolution

        self.selected_AI_model_path = default_model_path(selected_AI_model)
        self.upscale_factor = self._get_upscale_factor()

        self.inferenceSession: onnxruntime.InferenceSession | None = None
        self.input_name: str | None = None
        self.onnx_input: dict | None = None

    def _get_upscale_factor(self) -> int:
        if "x1" in self.selected_AI_model:
            return 1
        if "x2" in self.selected_AI_model:
            return 2
        if "x4" in self.selected_AI_model:
            return 4
        raise ValueError(f"Cannot derive upscale factor from model name: {self.selected_AI_model}")

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

    # Internal helpers

    def get_image_mode(self, image: numpy.ndarray) -> str:
        shape = image.shape
        if len(shape) == 2:
            return "Grayscale"
        if len(shape) == 3 and shape[2] == 3:
            return "RGB"
        if len(shape) == 3 and shape[2] == 4:
            return "RGBA"
        return "Unknown"

    def get_image_resolution(self, image: numpy.ndarray) -> tuple[int, int]:
        return image.shape[0], image.shape[1]

    def calculate_target_resolution(self, image: numpy.ndarray) -> tuple[int, int]:
        height, width = self.get_image_resolution(image)
        return height * self.upscale_factor, width * self.upscale_factor

    def resize_with_input_factor(self, image: numpy.ndarray) -> numpy.ndarray:
        old_height, old_width = self.get_image_resolution(image)

        new_width = int(old_width * self.input_resize_factor)
        new_height = int(old_height * self.input_resize_factor)

        new_width = new_width if new_width % 2 == 0 else new_width + 1
        new_height = new_height if new_height % 2 == 0 else new_height + 1

        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

    # Tiling

    def image_need_tilling(self, image: numpy.ndarray) -> bool:
        height, width = self.get_image_resolution(image)
        return height * width > self.tiles_resolution * self.tiles_resolution

    def add_alpha_channel(self, image: numpy.ndarray) -> numpy.ndarray:
        if image.shape[2] == 3:
            alpha = numpy.full((image.shape[0], image.shape[1], 1), 255, dtype=numpy.uint8)
            image = numpy.concatenate((image, alpha), axis=2)
        return image

    def calculate_tiles_number(self, image: numpy.ndarray) -> tuple[int, int]:
        height, width = self.get_image_resolution(image)
        tiles_x = (width + self.tiles_resolution - 1) // self.tiles_resolution
        tiles_y = (height + self.tiles_resolution - 1) // self.tiles_resolution
        return tiles_x, tiles_y

    def split_image_into_tiles(self, image: numpy.ndarray, tiles_x: int, tiles_y: int) -> list[numpy.ndarray]:
        img_height, img_width = self.get_image_resolution(image)

        tile_width = img_width // tiles_x
        tile_height = img_height // tiles_y

        tiles = []
        for y in range(tiles_y):
            y_start = y * tile_height
            y_end = (y + 1) * tile_height
            for x in range(tiles_x):
                x_start = x * tile_width
                x_end = (x + 1) * tile_width
                tiles.append(image[y_start:y_end, x_start:x_end])

        return tiles

    def combine_tiles_into_image(self, image: numpy.ndarray, tiles: list[numpy.ndarray], t_height: int, t_width: int, num_tiles_x: int) -> numpy.ndarray:
        image_mode = self.get_image_mode(image)
        if image_mode == "RGBA":
            tiled_image = numpy.zeros((t_height, t_width, 4), dtype=numpy.uint8)
        else:
            tiled_image = numpy.zeros((t_height, t_width, 3), dtype=numpy.uint8)

        for tile_index, actual_tile in enumerate(tiles):
            tile_height, tile_width = self.get_image_resolution(actual_tile)

            row = tile_index // num_tiles_x
            col = tile_index % num_tiles_x
            y_start = row * tile_height
            y_end = y_start + tile_height
            x_start = col * tile_width
            x_end = x_start + tile_width

            if image_mode == "RGBA":
                tiled_image[y_start:y_end, x_start:x_end] = self.add_alpha_channel(actual_tile)
            else:
                tiled_image[y_start:y_end, x_start:x_end] = actual_tile

        return tiled_image

    # Inference

    def normalize_image(self, image: numpy.ndarray) -> tuple[numpy.ndarray, float]:
        max_val = numpy.max(image)
        max_range = 65535.0 if max_val > 256 else 255.0
        image /= max_range
        return image, max_range

    def preprocess_image(self, image: numpy.ndarray) -> numpy.ndarray:
        image = numpy.transpose(image, (2, 0, 1))
        return numpy.expand_dims(image, axis=0)

    def onnxruntime_inference(self, image: numpy.ndarray) -> numpy.ndarray:
        self.onnx_input[self.input_name] = image
        return self.inferenceSession.run(None, self.onnx_input)[0]

    def postprocess_output(self, onnx_output: numpy.ndarray) -> numpy.ndarray:
        onnx_output = numpy.squeeze(onnx_output, axis=0)
        onnx_output = numpy.clip(onnx_output, 0, 1)
        return numpy.transpose(onnx_output, (1, 2, 0))

    def de_normalize_image(self, onnx_output: numpy.ndarray, max_range: float) -> numpy.ndarray:
        onnx_output *= max_range
        return onnx_output.astype(numpy.uint8) if max_range == 255 else onnx_output.astype(numpy.float32)

    def AI_upscale(self, image: numpy.ndarray) -> numpy.ndarray:
        image = image.astype(numpy.float32, copy=False)
        image_mode = self.get_image_mode(image)
        image, max_range = self.normalize_image(image)

        if image_mode == "RGB":
            image = self.preprocess_image(image)
            onnx_output = self.onnxruntime_inference(image)
            onnx_output = self.postprocess_output(onnx_output)
            return self.de_normalize_image(onnx_output, max_range)

        if image_mode == "RGBA":
            alpha = image[:, :, 3]
            image = image[:, :, :3]
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            image = image.astype(numpy.float32)
            alpha = alpha.astype(numpy.float32)

            image = self.preprocess_image(image)
            onnx_output_image = self.onnxruntime_inference(image)
            onnx_output_image = self.postprocess_output(onnx_output_image)
            onnx_output_image = cv2.cvtColor(onnx_output_image, cv2.COLOR_BGR2RGBA)

            alpha = numpy.expand_dims(alpha, axis=-1)
            alpha = numpy.repeat(alpha, 3, axis=-1)
            alpha = self.preprocess_image(alpha)
            onnx_output_alpha = self.onnxruntime_inference(alpha)
            onnx_output_alpha = self.postprocess_output(onnx_output_alpha)
            onnx_output_alpha = cv2.cvtColor(onnx_output_alpha, cv2.COLOR_RGB2GRAY)

            onnx_output_image[:, :, 3] = onnx_output_alpha
            return self.de_normalize_image(onnx_output_image, max_range)

        if image_mode == "Grayscale":
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

            image = self.preprocess_image(image)
            onnx_output = self.onnxruntime_inference(image)
            onnx_output = self.postprocess_output(onnx_output)
            return self.de_normalize_image(onnx_output, max_range)

        raise ValueError(f"Unsupported image mode: {image_mode}")

    def AI_upscale_with_tilling(self, image: numpy.ndarray) -> numpy.ndarray:
        t_height, t_width = self.calculate_target_resolution(image)
        tiles_x, tiles_y = self.calculate_tiles_number(image)
        tiles_list = self.split_image_into_tiles(image, tiles_x, tiles_y)
        tiles_list = [self.AI_upscale(tile) for tile in tiles_list]
        return self.combine_tiles_into_image(image, tiles_list, t_height, t_width, tiles_x)

    # Public API

    def AI_orchestration(self, image: numpy.ndarray) -> numpy.ndarray:
        if self.inferenceSession is None:
            self.inferenceSession = self._load_inferenceSession()
            self.input_name = self.inferenceSession.get_inputs()[0].name
            self.onnx_input = {self.input_name: None}

        resized_image = self.resize_with_input_factor(image)

        if self.image_need_tilling(resized_image):
            return self.AI_upscale_with_tilling(resized_image)
        return self.AI_upscale(resized_image)
