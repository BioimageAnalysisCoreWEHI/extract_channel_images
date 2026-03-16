nextflow.enable.dsl = 2

params.input_dir = null
params.pattern = '*.{tif,tiff,ome.tif,ome.tiff,qptiff,qptif}'
params.marker_mapping = null
params.outdir = 'results'
params.publish_dir_mode = 'copy'
params.validate_params = true

process EXTRACT_CHANNELS {
    tag "$prefix"
    label 'process_multi'

    conda "${projectDir}/environment.yml"
    container 'community.wave.seqera.io/library/tifffile_xarray_numpy_typer:f92759840da2dc33'

    publishDir "${params.outdir}", mode: params.publish_dir_mode

    input:
    val prefix
    path tiff
    val marker_mapping

    output:
    path "${prefix}"

    script:
    def markerArg = marker_mapping ? "--marker-mapping '${marker_mapping}'" : ''
    """
    python ${projectDir}/bin/extract_channels.py \\
        --input '$tiff' \\
        --output-dir '${prefix}' \\
        ${markerArg}
    """
}

workflow {
    if (!params.input_dir) {
        error "Missing required parameter: --input_dir"
    }

    def inputDir = file(params.input_dir)
    if (!inputDir.exists()) {
        error "Input directory does not exist: ${params.input_dir}"
    }

    def mappingPath = params.marker_mapping ? file(params.marker_mapping) : null
    if (params.marker_mapping && !mappingPath.exists()) {
        error "Marker mapping JSON does not exist: ${params.marker_mapping}"
    }

    Channel
        .fromPath("${params.input_dir}/${params.pattern}")
        .ifEmpty { error "No TIFF files found in ${params.input_dir} with pattern '${params.pattern}'" }
        .map { tiff ->
            def prefix = tiff.name.replaceAll(/(\.ome)?\.(tiff|tif|qptiff|qptif)$/,'')
            tuple(prefix, tiff, params.marker_mapping)
        }
        | EXTRACT_CHANNELS
}
