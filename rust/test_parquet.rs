use anyhow::{Context, Result};
use parquet::arrow::arrow_reader::ParquetRecordBatchReaderBuilder;
use std::fs::File;

fn main() -> Result<()> {
    let path = r"C:\Users\User\Documents\_web\_01_web\data\decoded_quotes\20251031\1503.parquet";
    println!("Reading: {}", path);

    let file = File::open(path)?;
    let builder = ParquetRecordBatchReaderBuilder::try_new(file)?;

    println!("Schema: {:?}", builder.schema());

    let mut reader = builder.build()?;

    if let Some(batch) = reader.next() {
        let batch = batch?;
        println!("\nBatch has {} rows", batch.num_rows());
        println!("Columns:");
        for (i, field) in batch.schema().fields().iter().enumerate() {
            let col = batch.column(i);
            println!("  {} - {} - {:?}", field.name(), field.data_type(), col.data_type());
        }
    }

    Ok(())
}
