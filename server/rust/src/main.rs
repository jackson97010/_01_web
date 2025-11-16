use actix_web::{get, web, App, HttpResponse, HttpServer, Result};
use actix_files as fs;
use actix_cors::Cors;
use serde::Serialize;
use std::path::PathBuf;
use std::fs as std_fs;

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
}

/// GET /api/dates - 取得所有可用日期
#[get("/api/dates")]
async fn get_dates() -> Result<HttpResponse> {
    let api_dir = PathBuf::from("../../frontend/static/api");

    if !api_dir.exists() {
        return Ok(HttpResponse::NotFound().json(ErrorResponse {
            error: "找不到資料目錄".to_string(),
        }));
    }

    let mut dates: Vec<String> = Vec::new();

    if let Ok(entries) = std_fs::read_dir(&api_dir) {
        for entry in entries.flatten() {
            if let Ok(file_type) = entry.file_type() {
                if file_type.is_dir() {
                    if let Some(name) = entry.file_name().to_str() {
                        if name.chars().all(|c| c.is_numeric()) && name.len() == 8 {
                            dates.push(name.to_string());
                        }
                    }
                }
            }
        }
    }

    dates.sort();
    dates.reverse();

    Ok(HttpResponse::Ok().json(dates))
}

/// GET /api/stocks/{date} - 取得指定日期的股票清單
#[get("/api/stocks/{date}")]
async fn get_stocks(date: web::Path<String>) -> Result<HttpResponse> {
    let date_dir = PathBuf::from(format!("../../frontend/static/api/{}", date));

    if !date_dir.exists() {
        return Ok(HttpResponse::NotFound().json(ErrorResponse {
            error: "找不到該日期".to_string(),
        }));
    }

    let mut stocks: Vec<String> = Vec::new();

    if let Ok(entries) = std_fs::read_dir(&date_dir) {
        for entry in entries.flatten() {
            if let Ok(file_type) = entry.file_type() {
                if file_type.is_file() {
                    if let Some(name) = entry.file_name().to_str() {
                        if name.ends_with(".json") {
                            let stock_code = name.trim_end_matches(".json");
                            stocks.push(stock_code.to_string());
                        }
                    }
                }
            }
        }
    }

    stocks.sort();

    Ok(HttpResponse::Ok().json(stocks))
}

/// GET /api/data/{date}/{stock_code} - 取得股票完整資料
#[get("/api/data/{date}/{stock_code}")]
async fn get_stock_data(path: web::Path<(String, String)>) -> Result<HttpResponse> {
    let (date, stock_code) = path.into_inner();
    let json_path = PathBuf::from(format!(
        "../../frontend/static/api/{}/{}.json",
        date, stock_code
    ));

    if !json_path.exists() {
        return Ok(HttpResponse::NotFound().json(ErrorResponse {
            error: "找不到資料".to_string(),
        }));
    }

    // 直接讀取並返回 JSON 檔案
    match std_fs::read_to_string(&json_path) {
        Ok(content) => {
            Ok(HttpResponse::Ok()
                .content_type("application/json")
                .insert_header(("Cache-Control", "public, max-age=3600"))
                .body(content))
        }
        Err(_) => Ok(HttpResponse::InternalServerError().json(ErrorResponse {
            error: "讀取資料失敗".to_string(),
        })),
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // 初始化日誌
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));

    let port = 5000u16;
    let host = "0.0.0.0";

    println!("================================================================================");
    println!("Stock Quote Viewer - 高效能伺服器 (Rust/Actix-Web)");
    println!("================================================================================");
    println!("伺服器啟動於: http://localhost:{}", port);
    println!("API 端點:");
    println!("  - http://localhost:{}/api/dates", port);
    println!("  - http://localhost:{}/api/stocks/{{date}}", port);
    println!("  - http://localhost:{}/api/data/{{date}}/{{stock_code}}", port);
    println!("前端頁面:");
    println!("  - http://localhost:{}/", port);
    println!("  - http://localhost:{}/index.html", port);
    println!("================================================================================");
    println!("按 Ctrl+C 停止伺服器");
    println!("================================================================================");

    HttpServer::new(|| {
        // 設定 CORS
        let cors = Cors::default()
            .allow_any_origin()
            .allow_any_method()
            .allow_any_header()
            .max_age(3600);

        App::new()
            .wrap(cors)
            // API 路由
            .service(get_dates)
            .service(get_stocks)
            .service(get_stock_data)
            // 靜態檔案服務
            .service(
                fs::Files::new("/static", "../../frontend/static")
                    .show_files_listing()
                    .use_last_modified(true)
            )
            // 首頁重定向
            .service(fs::Files::new("/", "../../frontend")
                .index_file("index.html")
                .use_last_modified(true))
    })
    .bind((host, port))?
    .run()
    .await
}
