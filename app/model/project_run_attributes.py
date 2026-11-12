
class ProjectRunAttributes:
    def __init__(self, confidence_level: int,
                 interface_to_use: list[int],
                 geojson_bounds: str,
                 ):
        self.confidence_level = confidence_level
        self.interface_to_use = interface_to_use
        self.geojson_bounding_box = geojson_bounds

        self.base_map_url = ""
        self.image_size = 1000
