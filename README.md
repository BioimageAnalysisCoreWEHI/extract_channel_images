# extract_channel_images

Small Nextflow pipeline for extracting individual channel images from multiplex TIFF images from COMET, MIBI, and OPAL.

## What it does

- Reads all TIFF images from an input folder.
- Auto-detects channel names from:
	- OME metadata (COMET / OPAL / generic OME-TIFF)
	- MIBI JSON page descriptions (`channel.target`)
	- MIBI `PageName` tags
- Optionally renames channels using a JSON marker mapping file.
- Writes one output TIFF per channel per input image.

## Inputs

- `--input_dir` (required): Folder containing TIFF files.
- `--marker_mapping` (optional): JSON file with `raw_channel_name -> output_channel_name`.
- `--outdir` (optional): Output folder (default: `results`).
- `--pattern` (optional): File glob (default: `*.{tif,tiff,ome.tif,ome.tiff,qptiff,qptif}`).

## Usage

Run with conda profile:

```bash
nextflow run main.nf \
	-profile conda \
	--input_dir /path/to/images \
	--marker_mapping /path/to/marker_mapping.json \
	--outdir /path/to/output
```

Run with container profile:

```bash
nextflow run main.nf \
	-profile docker \
	--input_dir /path/to/images \
	--marker_mapping /path/to/marker_mapping.json \
	--outdir /path/to/output
```

Run on HPC with Singularity:

```bash
nextflow run main.nf \
	-profile singularity,medium \
	--input_dir /path/to/images \
	--marker_mapping /path/to/marker_mapping.json \
	--outdir /path/to/output
```

Run for very large images on SLURM (combine runtime + resource profiles):

```bash
nextflow run main.nf \
	-profile conda,large \
	--input_dir /path/to/images \
	--marker_mapping /path/to/marker_mapping.json \
	--outdir /path/to/output
```

Run without mapping file:

```bash
nextflow run main.nf \
	-profile conda \
	--input_dir /path/to/images \
	--outdir /path/to/output
```

## Output layout

For each input image, the pipeline creates one folder in `outdir`:

- `<image_name>/`
	- `<channel_1>.tiff`
	- `<channel_2>.tiff`
	- ...

Channel names are sanitized for filenames. If multiple channels map to the same output name, numeric suffixes are added (for example `_2`, `_3`).

## Quick test

Generate tiny synthetic OPAL and MIBI test inputs and run the built-in test profile:

```bash
python tests/create_test_data.py
nextflow run main.nf -profile test
```

Test outputs are written to `tests/results`.
