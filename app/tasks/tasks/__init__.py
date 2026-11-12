__all__ = ["tile_image", "segment_process", "merge_tiles", "vectorize_tile_results", "merge_geo_packages",
           "get_function_name_from_alias", "apply_confidence"]

def get_function_name_from_alias(alias: str) -> str:
    if alias == "TileImagesSrc":
        return "tile_image"
    if alias == "SegmentProcess":
        return "segment_process"
    if alias == "MergeTiles":
        return "merge_tiles"
    if alias == "Vectorize":
        return "vectorize_tile_results"
    if alias == "MergeGeoPackages":
        return "merge_geo_packages"
    if alias == "ApplyConfidence":
        return "apply_confidence"
    return alias