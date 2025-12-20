use neon::prelude::*;
use serde::{Deserialize, Serialize};
use std::cmp::Ordering;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Trade {
    #[serde(rename = "Type")]
    type_field: String,
    #[serde(rename = "Timestamp")]
    timestamp: i64,
    #[serde(rename = "Datetime")]
    datetime: String,
    #[serde(rename = "Price")]
    price: Option<f64>,
    #[serde(rename = "Volume")]
    volume: Option<i32>,
    #[serde(rename = "BS_Flag")]
    bs_flag: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Depth {
    #[serde(rename = "Type")]
    type_field: String,
    #[serde(rename = "Timestamp")]
    timestamp: i64,
    #[serde(rename = "Datetime")]
    datetime: String,
    #[serde(rename = "BS_Flag")]
    bs_flag: Option<String>,

    // 買盤五檔
    #[serde(rename = "Bid1_Price")]
    bid1_price: Option<f64>,
    #[serde(rename = "Bid1_Volume")]
    bid1_volume: Option<i32>,
    #[serde(rename = "Bid2_Price")]
    bid2_price: Option<f64>,
    #[serde(rename = "Bid2_Volume")]
    bid2_volume: Option<i32>,
    #[serde(rename = "Bid3_Price")]
    bid3_price: Option<f64>,
    #[serde(rename = "Bid3_Volume")]
    bid3_volume: Option<i32>,
    #[serde(rename = "Bid4_Price")]
    bid4_price: Option<f64>,
    #[serde(rename = "Bid4_Volume")]
    bid4_volume: Option<i32>,
    #[serde(rename = "Bid5_Price")]
    bid5_price: Option<f64>,
    #[serde(rename = "Bid5_Volume")]
    bid5_volume: Option<i32>,

    // 賣盤五檔
    #[serde(rename = "Ask1_Price")]
    ask1_price: Option<f64>,
    #[serde(rename = "Ask1_Volume")]
    ask1_volume: Option<i32>,
    #[serde(rename = "Ask2_Price")]
    ask2_price: Option<f64>,
    #[serde(rename = "Ask2_Volume")]
    ask2_volume: Option<i32>,
    #[serde(rename = "Ask3_Price")]
    ask3_price: Option<f64>,
    #[serde(rename = "Ask3_Volume")]
    ask3_volume: Option<i32>,
    #[serde(rename = "Ask4_Price")]
    ask4_price: Option<f64>,
    #[serde(rename = "Ask4_Volume")]
    ask4_volume: Option<i32>,
    #[serde(rename = "Ask5_Price")]
    ask5_price: Option<f64>,
    #[serde(rename = "Ask5_Volume")]
    ask5_volume: Option<i32>,

    // 其他可能的字段
    #[serde(flatten)]
    other: serde_json::Map<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
enum ReplayRow {
    Trade(Trade),
    Depth(Depth),
}

impl ReplayRow {
    fn timestamp(&self) -> i64 {
        match self {
            ReplayRow::Trade(t) => t.timestamp,
            ReplayRow::Depth(d) => d.timestamp,
        }
    }

    fn type_field(&self) -> &str {
        match self {
            ReplayRow::Trade(t) => &t.type_field,
            ReplayRow::Depth(d) => &d.type_field,
        }
    }

    fn set_bs_flag(&mut self, flag: String) {
        match self {
            ReplayRow::Trade(t) => t.bs_flag = Some(flag),
            ReplayRow::Depth(d) => d.bs_flag = Some(flag),
        }
    }
}

// 高性能數據處理函數
fn prepare_replay_data(mut rows: Vec<ReplayRow>) -> Vec<ReplayRow> {
    // 1. 排序 - 使用穩定排序算法
    rows.sort_by(|a, b| {
        match a.timestamp().cmp(&b.timestamp()) {
            Ordering::Equal => {
                // Trade 排在 Depth 前面
                match (a.type_field(), b.type_field()) {
                    ("Trade", "Depth") => Ordering::Less,
                    ("Depth", "Trade") => Ordering::Greater,
                    _ => Ordering::Equal,
                }
            }
            other => other,
        }
    });

    // 2. 計算內外盤標記 - 使用高效的單次遍歷
    let mut last_depth: Option<(f64, f64)> = None; // (ask1, bid1)

    for row in &mut rows {
        match row {
            ReplayRow::Depth(depth) => {
                depth.bs_flag = Some("None".to_string());
                if let (Some(ask), Some(bid)) = (depth.ask1_price, depth.bid1_price) {
                    last_depth = Some((ask, bid));
                }
            }
            ReplayRow::Trade(trade) => {
                if let (Some(price), Some((ask1, bid1))) = (trade.price, last_depth) {
                    let flag = if price >= ask1 {
                        "Out"
                    } else if price <= bid1 {
                        "In"
                    } else {
                        "None"
                    };
                    trade.bs_flag = Some(flag.to_string());
                } else {
                    trade.bs_flag = Some("None".to_string());
                }
            }
        }
    }

    rows
}

// Neon 綁定：處理 JavaScript 數組（暫時移除，使用 JSON 版本）
fn process_replay_data(mut cx: FunctionContext) -> JsResult<JsString> {
    // 直接調用 JSON 版本
    process_replay_data_json(cx)
}

// 更簡單的版本：直接處理 JSON 字符串
fn process_replay_data_json(mut cx: FunctionContext) -> JsResult<JsString> {
    // 獲取 JSON 字符串
    let json_str = cx.argument::<JsString>(0)?.value(&mut cx);

    // 解析
    let rows: Vec<ReplayRow> = match serde_json::from_str(&json_str) {
        Ok(data) => data,
        Err(e) => return cx.throw_error(format!("JSON parse error: {}", e)),
    };

    // 處理
    let processed = prepare_replay_data(rows);

    // 序列化回 JSON
    let result_json = match serde_json::to_string(&processed) {
        Ok(json) => json,
        Err(e) => return cx.throw_error(format!("JSON stringify error: {}", e)),
    };

    Ok(cx.string(result_json))
}

// 性能測試函數：測試處理速度
fn benchmark_process(mut cx: FunctionContext) -> JsResult<JsNumber> {
    use std::time::Instant;

    let json_str = cx.argument::<JsString>(0)?.value(&mut cx);
    let rows: Vec<ReplayRow> = serde_json::from_str(&json_str)
        .or_else(|e| cx.throw_error(format!("Parse error: {}", e)))?;

    let start = Instant::now();
    let _processed = prepare_replay_data(rows);
    let duration = start.elapsed();

    Ok(cx.number(duration.as_millis() as f64))
}

// 導出模塊
#[neon::main]
fn main(mut cx: ModuleContext) -> NeonResult<()> {
    cx.export_function("processReplayData", process_replay_data)?;
    cx.export_function("processReplayDataJson", process_replay_data_json)?;
    cx.export_function("benchmark", benchmark_process)?;
    Ok(())
}
