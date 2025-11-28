use anyhow::{Context, Result};
use arrow::array::{
    Array, Float64Array, Int64Array, StringArray, TimestampMicrosecondArray, TimestampNanosecondArray,
};
use arrow::datatypes::DataType;
use chrono::DateTime;
use parquet::arrow::arrow_reader::ParquetRecordBatchReaderBuilder;
use serde::{Deserialize, Serialize};
use std::fs::{self, File};
use std::path::{Path, PathBuf};

// ==================== Data Structures ====================

#[derive(Debug, Clone, Serialize, Deserialize)]
struct PriceVolume {
    price: f64,
    volume: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Trade {
    time: String,
    price: f64,
    volume: i64,
    inner_outer: String,
    flag: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct DepthSnapshot {
    timestamp: String,
    bids: Vec<PriceVolume>,
    asks: Vec<PriceVolume>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Depth {
    bids: Vec<PriceVolume>,
    asks: Vec<PriceVolume>,
    timestamp: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Chart {
    timestamps: Vec<String>,
    prices: Vec<f64>,
    volumes: Vec<i64>,
    total_volumes: Vec<i64>,
    vwap: Vec<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Stats {
    current_price: f64,
    open_price: f64,
    high_price: f64,
    low_price: f64,
    avg_price: f64,
    total_volume: i64,
    trade_count: usize,
    change: f64,
    change_pct: f64,
}

#[derive(Debug, Serialize, Deserialize)]
struct StockData {
    chart: Option<Chart>,
    depth: Option<Depth>,
    depth_history: Vec<DepthSnapshot>,
    trades: Vec<Trade>,
    stats: Option<Stats>,
    stock_code: String,
    date: String,
}

#[derive(Debug, Clone)]
struct TradeRecord {
    datetime: i64,
    price: f64,
    volume: i64,
    flag: i64,
}

#[derive(Debug, Clone)]
struct DepthRecord {
    datetime: i64,
    bid_prices: [Option<f64>; 5],
    bid_volumes: [Option<i64>; 5],
    ask_prices: [Option<f64>; 5],
    ask_volumes: [Option<i64>; 5],
}

// ==================== Helper Functions ====================

fn timestamp_to_datetime_str(timestamp_us: i64) -> String {
    match DateTime::from_timestamp_micros(timestamp_us) {
        Some(datetime) => datetime.format("%Y-%m-%d %H:%M:%S%.6f").to_string(),
        None => "1970-01-01 00:00:00.000000".to_string(),
    }
}

fn extract_date_from_timestamp(timestamp_us: i64) -> String {
    match DateTime::from_timestamp_micros(timestamp_us) {
        Some(datetime) => datetime.format("%Y%m%d").to_string(),
        None => "19700101".to_string(),
    }
}

fn determine_inner_outer(current_price: f64, prev_bid1: Option<f64>, prev_ask1: Option<f64>) -> String {
    if let Some(ask1) = prev_ask1 {
        if current_price >= ask1 {
            return "outer".to_string();  // 外盤（買進）
        }
    }
    if let Some(bid1) = prev_bid1 {
        if current_price <= bid1 {
            return "inner".to_string();  // 內盤（賣出）
        }
    }
    "neutral".to_string()  // 中立
}

// ==================== Parquet Reading ====================

fn read_parquet_file(path: &Path) -> Result<(Vec<TradeRecord>, Vec<DepthRecord>, String, String)> {
    let file = File::open(path)?;
    let builder = ParquetRecordBatchReaderBuilder::try_new(file)?;
    let mut reader = builder.build()?;

    let mut trades = Vec::new();
    let mut depths = Vec::new();
    let mut stock_code = String::new();
    let mut date_str = String::new();

    while let Some(batch) = reader.next() {
        let batch = batch?;

        // Get columns
        let type_col = batch
            .column_by_name("Type")
            .context("Type column not found")?
            .as_any()
            .downcast_ref::<StringArray>()
            .context("Type column is not StringArray")?;

        let stock_code_col = batch
            .column_by_name("StockCode")
            .context("StockCode column not found")?
            .as_any()
            .downcast_ref::<StringArray>()
            .context("StockCode column is not StringArray")?;

        let datetime_col = batch
            .column_by_name("Datetime")
            .context("Datetime column not found")?;

        // Get datetime values based on type
        let datetime_values: Vec<i64> = match datetime_col.data_type() {
            DataType::Timestamp(_, _) => {
                // Try nanosecond timestamp first (from pandas datetime64[ns])
                if let Some(ts_array) = datetime_col.as_any().downcast_ref::<TimestampNanosecondArray>() {
                    (0..ts_array.len())
                        .map(|i| ts_array.value(i) / 1000) // Convert ns to us
                        .collect()
                } else if let Some(ts_array) = datetime_col.as_any().downcast_ref::<TimestampMicrosecondArray>() {
                    (0..ts_array.len())
                        .map(|i| ts_array.value(i))
                        .collect()
                } else {
                    anyhow::bail!("Failed to cast Datetime to Timestamp array")
                }
            }
            DataType::Int64 => {
                let int_array = datetime_col
                    .as_any()
                    .downcast_ref::<Int64Array>()
                    .context("Failed to cast Datetime to Int64Array")?;
                (0..int_array.len())
                    .map(|i| int_array.value(i) * 1000) // Convert ms to us
                    .collect()
            }
            DataType::Float64 => {
                let float_array = datetime_col
                    .as_any()
                    .downcast_ref::<Float64Array>()
                    .context("Failed to cast Datetime to Float64Array")?;
                (0..float_array.len())
                    .map(|i| (float_array.value(i) * 1000.0) as i64) // Convert ms to us
                    .collect()
            }
            _ => anyhow::bail!("Unsupported Datetime column type: {:?}", datetime_col.data_type()),
        };

        // Extract stock code and date
        if stock_code.is_empty() && stock_code_col.len() > 0 {
            stock_code = stock_code_col.value(0).trim().to_string();
            date_str = extract_date_from_timestamp(datetime_values[0]);
        }

        // Process each row
        for i in 0..batch.num_rows() {
            let row_type = type_col.value(i);
            let datetime = datetime_values[i];

            if row_type == "Trade" {
                let price = get_float_value(&batch, "Price", i)?;
                let volume = get_int_value(&batch, "Volume", i)?;
                let flag = get_int_value(&batch, "Flag", i)?;

                trades.push(TradeRecord {
                    datetime,
                    price,
                    volume,
                    flag,
                });
            } else if row_type == "Depth" {
                let mut bid_prices = [None; 5];
                let mut bid_volumes = [None; 5];
                let mut ask_prices = [None; 5];
                let mut ask_volumes = [None; 5];

                for j in 1..=5 {
                    bid_prices[j - 1] = get_optional_float_value(&batch, &format!("Bid{}_Price", j), i);
                    bid_volumes[j - 1] = get_optional_int_value(&batch, &format!("Bid{}_Volume", j), i);
                    ask_prices[j - 1] = get_optional_float_value(&batch, &format!("Ask{}_Price", j), i);
                    ask_volumes[j - 1] = get_optional_int_value(&batch, &format!("Ask{}_Volume", j), i);
                }

                depths.push(DepthRecord {
                    datetime,
                    bid_prices,
                    bid_volumes,
                    ask_prices,
                    ask_volumes,
                });
            }
        }
    }

    Ok((trades, depths, stock_code, date_str))
}

fn get_float_value(batch: &arrow::record_batch::RecordBatch, col_name: &str, index: usize) -> Result<f64> {
    let col = batch
        .column_by_name(col_name)
        .context(format!("{} column not found", col_name))?;

    if let Some(float_array) = col.as_any().downcast_ref::<Float64Array>() {
        Ok(float_array.value(index))
    } else {
        anyhow::bail!("{} column is not Float64Array", col_name)
    }
}

fn get_int_value(batch: &arrow::record_batch::RecordBatch, col_name: &str, index: usize) -> Result<i64> {
    let col = batch
        .column_by_name(col_name)
        .context(format!("{} column not found", col_name))?;

    if let Some(int_array) = col.as_any().downcast_ref::<Int64Array>() {
        Ok(int_array.value(index))
    } else if let Some(float_array) = col.as_any().downcast_ref::<Float64Array>() {
        // Handle float64 columns (due to NaN values in parquet)
        Ok(float_array.value(index) as i64)
    } else {
        anyhow::bail!("{} column is neither Int64Array nor Float64Array", col_name)
    }
}

fn get_optional_float_value(batch: &arrow::record_batch::RecordBatch, col_name: &str, index: usize) -> Option<f64> {
    batch
        .column_by_name(col_name)
        .and_then(|col| col.as_any().downcast_ref::<Float64Array>())
        .and_then(|arr| if arr.is_null(index) { None } else { Some(arr.value(index)) })
}

fn get_optional_int_value(batch: &arrow::record_batch::RecordBatch, col_name: &str, index: usize) -> Option<i64> {
    if let Some(col) = batch.column_by_name(col_name) {
        if let Some(int_array) = col.as_any().downcast_ref::<Int64Array>() {
            if int_array.is_null(index) {
                None
            } else {
                Some(int_array.value(index))
            }
        } else if let Some(float_array) = col.as_any().downcast_ref::<Float64Array>() {
            // Handle float64 columns (due to NaN values in parquet)
            if float_array.is_null(index) || float_array.value(index).is_nan() {
                None
            } else {
                Some(float_array.value(index) as i64)
            }
        } else {
            None
        }
    } else {
        None
    }
}

// ==================== Data Processing ====================

fn process_stock_file(parquet_path: &Path, output_path: &Path) -> Result<bool> {
    // Read parquet file
    let (mut trades, depths, stock_code, date_str) = read_parquet_file(parquet_path)
        .context(format!("Failed to read parquet: {:?}", parquet_path))?;

    if trades.is_empty() && depths.is_empty() {
        println!("  警告: {:?} 沒有資料", parquet_path.file_name().unwrap());
        return Ok(false);
    }

    // Process trades
    let processed_trades = process_trades(&mut trades, &depths)?;

    // Process depth history
    let depth_history = process_depth_history(&depths)?;

    // Get current depth (latest)
    let depth = depth_history.last().map(|d| Depth {
        bids: d.bids.clone(),
        asks: d.asks.clone(),
        timestamp: d.timestamp.clone(),
    });

    // Process chart data
    let chart = if !trades.is_empty() {
        Some(process_chart(&trades)?)
    } else {
        None
    };

    // Calculate stats
    let stats = if !trades.is_empty() {
        Some(calculate_stats(&trades)?)
    } else {
        None
    };

    // Create result
    let result = StockData {
        chart,
        depth,
        depth_history,
        trades: processed_trades,
        stats,
        stock_code,
        date: date_str,
    };

    // Write to JSON
    if let Some(parent) = output_path.parent() {
        fs::create_dir_all(parent)?;
    }
    let file = File::create(output_path)?;
    serde_json::to_writer_pretty(file, &result)?;

    Ok(true)
}

fn process_trades(trades: &mut [TradeRecord], depths: &[DepthRecord]) -> Result<Vec<Trade>> {
    // Sort trades by datetime descending (newest first)
    trades.sort_by(|a, b| b.datetime.cmp(&a.datetime));

    let mut result = Vec::new();

    for trade in trades.iter() {
        // Find previous depth before this trade
        let prev_depth = depths
            .iter()
            .filter(|d| d.datetime < trade.datetime)
            .last();

        let (prev_bid1, prev_ask1) = if let Some(depth) = prev_depth {
            (depth.bid_prices[0], depth.ask_prices[0])
        } else {
            (None, None)
        };

        let inner_outer = determine_inner_outer(trade.price, prev_bid1, prev_ask1);

        result.push(Trade {
            time: timestamp_to_datetime_str(trade.datetime),
            price: trade.price,
            volume: trade.volume,
            inner_outer,
            flag: trade.flag,
        });
    }

    Ok(result)
}

fn process_depth_history(depths: &[DepthRecord]) -> Result<Vec<DepthSnapshot>> {
    let mut result = Vec::new();

    for depth in depths {
        let mut bids = Vec::new();
        let mut asks = Vec::new();

        // Process bids
        for i in 0..5 {
            if let (Some(price), Some(volume)) = (depth.bid_prices[i], depth.bid_volumes[i]) {
                bids.push(PriceVolume { price, volume });
            }
        }

        // Process asks
        for i in 0..5 {
            if let (Some(price), Some(volume)) = (depth.ask_prices[i], depth.ask_volumes[i]) {
                asks.push(PriceVolume { price, volume });
            }
        }

        result.push(DepthSnapshot {
            timestamp: timestamp_to_datetime_str(depth.datetime),
            bids,
            asks,
        });
    }

    Ok(result)
}

fn process_chart(trades: &[TradeRecord]) -> Result<Chart> {
    // Sort by datetime ascending
    let mut sorted_trades = trades.to_vec();
    sorted_trades.sort_by(|a, b| a.datetime.cmp(&b.datetime));

    let timestamps: Vec<String> = sorted_trades
        .iter()
        .map(|t| timestamp_to_datetime_str(t.datetime))
        .collect();

    let prices: Vec<f64> = sorted_trades.iter().map(|t| t.price).collect();
    let volumes: Vec<i64> = sorted_trades.iter().map(|t| t.volume).collect();

    // Calculate cumulative volume
    let mut cumsum = 0i64;
    let total_volumes: Vec<i64> = volumes
        .iter()
        .map(|&v| {
            cumsum += v;
            cumsum
        })
        .collect();

    // Calculate VWAP
    let mut cumulative_amount = 0.0;
    let mut cumulative_volume = 0i64;
    let vwap: Vec<f64> = sorted_trades
        .iter()
        .map(|t| {
            cumulative_amount += t.price * t.volume as f64;
            cumulative_volume += t.volume;
            if cumulative_volume > 0 {
                cumulative_amount / cumulative_volume as f64
            } else {
                0.0
            }
        })
        .collect();

    Ok(Chart {
        timestamps,
        prices,
        volumes,
        total_volumes,
        vwap,
    })
}

fn calculate_stats(trades: &[TradeRecord]) -> Result<Stats> {
    // Sort by datetime ascending
    let mut sorted_trades = trades.to_vec();
    sorted_trades.sort_by(|a, b| a.datetime.cmp(&b.datetime));

    let open_price = sorted_trades.first().unwrap().price;
    let current_price = sorted_trades.last().unwrap().price;

    let high_price = sorted_trades.iter().map(|t| t.price).fold(f64::NEG_INFINITY, f64::max);
    let low_price = sorted_trades.iter().map(|t| t.price).fold(f64::INFINITY, f64::min);

    // Calculate weighted average price
    let total_amount: f64 = sorted_trades.iter().map(|t| t.price * t.volume as f64).sum();
    let total_volume: i64 = sorted_trades.iter().map(|t| t.volume).sum();
    let avg_price = if total_volume > 0 {
        total_amount / total_volume as f64
    } else {
        0.0
    };

    let trade_count = sorted_trades.len();
    let change = current_price - open_price;
    let change_pct = if open_price > 0.0 {
        (change / open_price) * 100.0
    } else {
        0.0
    };

    Ok(Stats {
        current_price,
        open_price,
        high_price,
        low_price,
        avg_price,
        total_volume,
        trade_count,
        change,
        change_pct,
    })
}

// ==================== Main Logic ====================

fn main() -> Result<()> {
    println!("{}", "=".repeat(80));
    println!("Parquet 轉 JSON 轉換程式（Rust 版本）");
    println!("{}", "=".repeat(80));

    // Get paths
    let current_dir = std::env::current_dir()?;
    let project_root = current_dir;
    let decoded_dir = project_root.join("data").join("decoded_quotes");
    let output_dir = project_root.join("frontend").join("static").join("api");

    if !decoded_dir.exists() {
        println!("錯誤: 找不到解碼目錄 {:?}", decoded_dir);
        println!("請先執行 decode_quotes.py 或 batch_decode_quotes.py");
        return Ok(());
    }

    // Scan date directories
    let mut date_dirs: Vec<String> = fs::read_dir(&decoded_dir)?
        .filter_map(|entry| {
            let entry = entry.ok()?;
            let path = entry.path();
            if path.is_dir() {
                let name = path.file_name()?.to_str()?.to_string();
                if name.chars().all(|c| c.is_ascii_digit()) {
                    return Some(name);
                }
            }
            None
        })
        .collect();

    date_dirs.sort();

    if date_dirs.is_empty() {
        println!("\n沒有找到日期資料");
        return Ok(());
    }

    println!(
        "\n找到 {} 個日期: {} ~ {}",
        date_dirs.len(),
        date_dirs.first().unwrap(),
        date_dirs.last().unwrap()
    );

    let mut total_converted = 0;
    let mut total_failed = 0;

    // Process each date
    for date_str in date_dirs {
        println!("\n處理日期: {}", date_str);

        let date_input_dir = decoded_dir.join(&date_str);
        let date_output_dir = output_dir.join(&date_str);

        // Get all parquet files
        let pattern = format!("{}/*.parquet", date_input_dir.display());
        let parquet_files: Vec<PathBuf> = glob::glob(&pattern)?
            .filter_map(|p| p.ok())
            .collect();

        if parquet_files.is_empty() {
            println!("  沒有找到 parquet 檔案");
            continue;
        }

        println!("  找到 {} 個股票", parquet_files.len());

        let mut converted = 0;
        let mut failed = 0;

        for parquet_path in &parquet_files {
            let stock_code = parquet_path
                .file_stem()
                .and_then(|s| s.to_str())
                .unwrap_or("unknown");
            let output_path = date_output_dir.join(format!("{}.json", stock_code));

            // Check if already exists and is newer
            if output_path.exists() {
                let parquet_mtime = fs::metadata(&parquet_path)?.modified()?;
                let json_mtime = fs::metadata(&output_path)?.modified()?;

                if json_mtime > parquet_mtime {
                    continue; // Skip if JSON is newer
                }
            }

            // Convert
            match process_stock_file(&parquet_path, &output_path) {
                Ok(true) => {
                    converted += 1;
                    if converted % 10 == 0 {
                        println!("  已轉換: {}/{}", converted, parquet_files.len());
                    }
                }
                Ok(false) => {} // Empty file, not counted as failure
                Err(e) => {
                    println!("  錯誤 {}: {:?}", stock_code, e);
                    failed += 1;
                    // Only show first few errors in detail
                    if failed <= 3 {
                        eprintln!("    詳細錯誤: {:#?}", e);
                    }
                }
            }
        }

        let skipped = parquet_files.len() - converted - failed;
        println!(
            "  完成: 成功={}, 失敗={}, 跳過={}",
            converted, failed, skipped
        );
        total_converted += converted;
        total_failed += failed;
    }

    println!("\n{}", "=".repeat(80));
    println!("轉換完成！");
    println!("總共轉換: {} 個檔案", total_converted);
    if total_failed > 0 {
        println!("失敗: {} 個檔案", total_failed);
    }
    println!("輸出目錄: {:?}", output_dir);
    println!("{}", "=".repeat(80));

    Ok(())
}
