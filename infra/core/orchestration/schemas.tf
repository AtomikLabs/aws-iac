resource "aws_glue_registry" "glue-registry" {
    registry_name = "${local.environment}-glue-registry"
}

resource "aws_glue_schema" "arxiv_research_ingestion_event_schema" {
    schema_name = "${local.environment}-arxiv_research-ingestion-event-schema"
    compatibility = "BACKWARD_COMPATIBLE"
    data_format = "AVRO"
    registry_arn = aws_glue_registry.glue-registry.arn
    schema_definition = file("${path.module}/schemas/arxiv_research_ingestion_event_schema.avsc")
}

