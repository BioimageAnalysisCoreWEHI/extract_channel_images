#!/usr/bin/env python3
import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Optional

import numpy as np
import tifffile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract individual channel TIFFs from COMET, MIBI, and OPAL images."
    )
    parser.add_argument("--input", required=True, type=Path, help="Input TIFF image path")
    parser.add_argument("--output-dir", required=True, type=Path, help="Output directory")
    parser.add_argument(
        "--marker-mapping",
        type=Path,
        default=None,
        help="Optional JSON mapping of raw channel name -> output channel name",
    )
    return parser.parse_args()


def local_tag_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def parse_ome_channel_names(ome_xml: str) -> list[str]:
    root = ET.fromstring(ome_xml)

    pixels = None
    for elem in root.iter():
        if local_tag_name(elem.tag) == "Pixels":
            pixels = elem
            break

    if pixels is None:
        return []

    names: list[str] = []
    for idx, elem in enumerate(list(pixels)):
        if local_tag_name(elem.tag) == "Channel":
            names.append(elem.get("Name") or elem.get("ID") or f"channel_{idx}")

    return names


def parse_mibi_json_channel_names(tif: tifffile.TiffFile) -> list[str]:
    channel_names: list[str] = []
    for page in tif.pages:
        desc = page.description
        if not desc:
            return []
        payload = json.loads(desc)
        name = payload.get("channel.target")
        if not name:
            return []
        channel_names.append(name)
    return channel_names


def parse_pagename_channel_names(tif: tifffile.TiffFile) -> list[str]:
    names: list[str] = []
    for idx, page in enumerate(tif.pages):
        page_name_tag = page.tags.get("PageName")
        if page_name_tag is None:
            return []
        value = str(page_name_tag.value).strip()
        names.append(value if value else f"channel_{idx}")
    return names


def detect_channel_names(tif: tifffile.TiffFile, n_channels: int) -> list[str]:
    first_page = tif.pages[0]

    # MIBI per-page JSON descriptions
    try:
        names = parse_mibi_json_channel_names(tif)
        if names:
            return names
    except Exception:
        pass

    # OME metadata (COMET / OPAL / generic OME-TIFF)
    try:
        ome_xml = tif.ome_metadata or first_page.description
        if ome_xml:
            names = parse_ome_channel_names(ome_xml)
            if names:
                return names
    except Exception:
        pass

    # MIBI PageName tag fallback
    try:
        names = parse_pagename_channel_names(tif)
        if names:
            return names
    except Exception:
        pass

    return [f"channel_{i}" for i in range(n_channels)]


def sanitize_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>| ]', "_", name).strip("_") or "channel"


def make_unique(names: list[str]) -> list[str]:
    counts = Counter()
    unique_names = []
    for name in names:
        counts[name] += 1
        if counts[name] == 1:
            unique_names.append(name)
        else:
            unique_names.append(f"{name}_{counts[name]}")
    return unique_names


def load_mapping(mapping_file: Optional[Path]) -> dict[str, str]:
    if mapping_file is None:
        return {}
    with mapping_file.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Marker mapping JSON must be an object of raw_name -> clean_name")
    return {str(k): str(v) for k, v in payload.items()}


def to_channel_first(array: np.ndarray, axes: str, n_channels: int) -> np.ndarray:
    axes_upper = axes.upper()
    if "C" in axes_upper:
        c_idx = axes_upper.index("C")
        return np.moveaxis(array, c_idx, 0)

    # Fallback for files where channel is represented by stacked pages
    if array.ndim >= 3 and array.shape[0] == n_channels:
        return array

    if n_channels == 1:
        return array[np.newaxis, ...]

    raise ValueError(f"Could not locate channel axis in shape={array.shape}, axes='{axes}'")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    mapping = load_mapping(args.marker_mapping)

    with tifffile.TiffFile(args.input) as tif:
        data = tif.asarray()
        axes = tif.series[0].axes if tif.series else ""

        # Estimate channel count for name detection
        if "C" in axes.upper():
            n_channels = data.shape[axes.upper().index("C")]
        else:
            n_channels = len(tif.pages) if len(tif.pages) > 1 else 1

        raw_names = detect_channel_names(tif, n_channels)

    c_first = to_channel_first(data, axes, len(raw_names))

    if c_first.shape[0] != len(raw_names):
        raise ValueError(
            f"Channel mismatch: data has {c_first.shape[0]} channels but metadata has {len(raw_names)} names"
        )

    renamed = [mapping.get(name, name) for name in raw_names]
    safe_names = [sanitize_name(name) for name in renamed]
    unique_names = make_unique(safe_names)

    print(f"Input image: {args.input}")
    print(f"Axes: {axes} | Shape: {data.shape} | Channels: {len(raw_names)}")
    if args.marker_mapping:
        print(f"Loaded mapping file: {args.marker_mapping}")

    for idx, (raw_name, out_name) in enumerate(zip(raw_names, unique_names)):
        channel_data = c_first[idx]
        out_path = args.output_dir / f"{out_name}.tiff"
        # Always write uint16 so downstream tools (e.g. CellTune) receive a
        # consistent dtype regardless of the source instrument.  MIBI images
        # are stored as float32 ion counts (small non-negative integers), so
        # the cast is lossless.  COMET images are already uint16.
        if channel_data.dtype != np.uint16:
            original_dtype = channel_data.dtype
            channel_data = channel_data.astype(np.uint16)
            print(f"[{idx:02d}] {raw_name} -> {out_path.name}  (converted {original_dtype} -> uint16)")
        else:
            print(f"[{idx:02d}] {raw_name} -> {out_path.name}")
        tifffile.imwrite(str(out_path), channel_data)


if __name__ == "__main__":
    main()
