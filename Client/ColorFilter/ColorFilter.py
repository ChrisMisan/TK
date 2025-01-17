import json
from . import PixelMetrics

from typing import Sequence
from . import Color
from PIL import ImageStat, Image
from Utils import Utils

SERVICE_NAME = "color service"
STAT_METRICS = {'max', 'min', 'mean', 'median', 'rms'}
PIXEL_METRICS = {'percentage'}


def get_stat_based_metric(metric: Color.ColorMetric):
    return {
        "max": lambda stat: map(lambda x: x[1], stat.extrema),
        "min": lambda stat: map(lambda x: x[0], stat.extrema),
        "mean": lambda stat: stat.mean,
        "median": lambda stat: stat.median,
        "rms": lambda stat: stat.rms
    }[metric.name]


def get_pixel_based_metric(metric: Color.ColorMetric):
    return {
        "percentage": PixelMetrics.color_percentage
    }[metric.name]


def get_filter_func(params):
    comparator = Utils.get_comparator(params.comparator, params.threshold)

    if params.metric.name in STAT_METRICS:
        metric = get_stat_based_metric(params.metric)

        def is_compliant(path):
            calc_metric = list(metric(ImageStat.Stat(Image.open(path))))
            if len(calc_metric) > 2:
                return all(map(
                    comparator,
                    calc_metric,
                    params.color
                ))
            elif len(calc_metric) == 1:
                colors = (params.color[0] + params.color[1] + params.color[2]) / 3
                return comparator(calc_metric[0], colors)
            else:  # This is not a normal image. I refuse to return it.
                return False
    elif params.metric.name in PIXEL_METRICS:
        metric = get_pixel_based_metric(params.metric)

        def is_compliant(path):
            print(path, end='-> ')
            image = Image.open(path)
            data = list(image.getdata())
            w, h = image.size
            total = w * h
            bound_metric = metric(data[0], params.color, params.tolerance)
            compliant_pixels = list(filter(lambda x: bound_metric(x), data))

            percent = 100 * len(compliant_pixels) / total
            print(percent)
            return comparator(percent, params.percent_threshold)

    else:
        def is_compliant(_):
            return True

    return is_compliant


def process_request(body: str) -> Sequence[str]:
    request = json.loads(body)
    paths = request['paths']
    raw_params = request['params']
    params = Color.ColorParams.from_object(raw_params)
    is_compliant = get_filter_func(params)

    result = list(filter(is_compliant, paths))
    return result


def process_single(target):
    params = Color.ColorParams.from_grpc(target)
    is_compliant = get_filter_func(params)

    return is_compliant(target.path)
