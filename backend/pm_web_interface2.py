"""
Complete PM Intelligence Dashboard for Railway Deployment
Includes file upload interface, processing, and analytics dashboard
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# Create FastAPI app
app = FastAPI(title="PM Intelligence Dashboard", version="1.0.0")

# Storage manager for file handling
class FileStorageManager:
    def __init__(self, storage_base_path: str = "pm_storage"):
        self.base_path = Path(storage_base_path)
        self.uploads_path = self.base_path / "uploads"
        self.processed_path = self.base_path / "processed"
        self.results_path = self.base_path / "results"
        
        # Create directories
        for path in [self.uploads_path, self.processed_path, self.results_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def save_uploaded_file(self, file: UploadFile) -> Path:
        """Save uploaded file to storage"""
        file_path = self.uploads_path / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return file_path
    
    def process_all_uploaded_files(self) -> Dict[str, Any]:
        """Process all uploaded files"""
        uploaded_files = list(self.uploads_path.glob("*"))
        results = {
            "total_files": len(uploaded_files),
            "successful_files": 0,
            "failed_files": 0,
            "processed_files": [],
            "errors": []
        }
        
        for file_path in uploaded_files:
            try:
                # Simulate processing
                if file_path.suffix.lower() in ['.xlsx', '.xls', '.csv', '.json', '.txt', '.pptx']:
                    # Move to processed folder
                    processed_file = self.processed_path / file_path.name
                    shutil.move(str(file_path), str(processed_file))
                    
                    results["successful_files"] += 1
                    results["processed_files"].append({
                        "filename": file_path.name,
                        "size": processed_file.stat().st_size,
                        "processed_at": datetime.now().isoformat(),
                        "status": "success"
                    })
                else:
                    results["failed_files"] += 1
                    results["errors"].append(f"Unsupported file type: {file_path.name}")
                    
            except Exception as e:
                results["failed_files"] += 1
                results["errors"].append(f"Error processing {file_path.name}: {str(e)}")
        
        # Save results
        results_file = self.results_path / f"processing_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        return results
    
    def get_processed_data_summary(self) -> Dict[str, Any]:
        """Get summary of all processed data"""
        processed_files = list(self.processed_path.glob("*"))
        result_files = list(self.results_path.glob("*.json"))
        
        total_processed = len(processed_files)
        total_size = sum(f.stat().st_size for f in processed_files)
        
        return {
            "total_processed_files": total_processed,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "processing_sessions": len(result_files),
            "last_processed": max([f.stat().st_mtime for f in processed_files]) if processed_files else None,
            "file_types": {}
        }

# Initialize storage manager
storage_manager = FileStorageManager()

# Routes
@app.get("/", response_class=HTMLResponse)
async def serve_main_interface():
    """Serve the main PM Intelligence Dashboard interface"""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PM Intelligence Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 40px; color: white; }
        .header h1 { font-size: 3rem; font-weight: 700; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .header p { font-size: 1.2rem; opacity: 0.9; margin-bottom: 30px; }
        .main-card {
            background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.2);
            overflow: hidden; margin-bottom: 30px;
        }
        .card-header {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            color: white; padding: 30px; text-align: center;
        }
        .card-header h2 { font-size: 2rem; margin-bottom: 10px; }
        .card-header p { opacity: 0.9; font-size: 1.1rem; }
        .upload-area { padding: 40px; text-align: center; }
        .file-drop-zone {
            border: 3px dashed #cbd5e1; border-radius: 15px; padding: 60px 20px;
            background: #f8fafc; transition: all 0.3s ease; cursor: pointer; margin-bottom: 30px;
        }
        .file-drop-zone:hover, .file-drop-zone.dragover {
            border-color: #4f46e5; background: #f0f4ff; transform: translateY(-2px);
        }
        .upload-icon {
            width: 80px; height: 80px; margin: 0 auto 20px;
            background: linear-gradient(135deg, #4f46e5, #7c3aed); border-radius: 50%;
            display: flex; align-items: center; justify-content: center; color: white; font-size: 2rem;
        }
        .upload-text h3 { font-size: 1.5rem; margin-bottom: 10px; color: #1e293b; }
        .upload-text p { color: #64748b; font-size: 1rem; margin-bottom: 20px; }
        .file-input { display: none; }
        .upload-btn {
            background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white; border: none;
            padding: 15px 30px; border-radius: 10px; font-size: 1rem; cursor: pointer;
            transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
        }
        .upload-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(79, 70, 229, 0.4); }
        .file-list { margin-top: 30px; text-align: left; }
        .file-item {
            display: flex; align-items: center; justify-content: space-between;
            background: #f1f5f9; border-radius: 10px; padding: 15px; margin-bottom: 10px;
        }
        .file-info { display: flex; align-items: center; }
        .file-icon {
            width: 40px; height: 40px; background: #4f46e5; color: white; border-radius: 8px;
            display: flex; align-items: center; justify-content: center; margin-right: 15px; font-weight: bold;
        }
        .file-details h4 { font-size: 1rem; margin-bottom: 2px; color: #1e293b; }
        .file-details p { font-size: 0.875rem; color: #64748b; }
        .remove-btn {
            background: #ef4444; color: white; border: none; padding: 8px 15px;
            border-radius: 6px; cursor: pointer; font-size: 0.875rem; transition: all 0.3s ease;
        }
        .remove-btn:hover { background: #dc2626; }
        .process-section { padding: 30px 40px; background: #f8fafc; border-top: 1px solid #e2e8f0; }
        .process-btn {
            background: linear-gradient(135deg, #059669, #10b981); color: white; border: none;
            padding: 18px 40px; border-radius: 12px; font-size: 1.1rem; font-weight: 600;
            cursor: pointer; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(5, 150, 105, 0.3);
            width: 100%; max-width: 300px; margin: 0 auto; display: block;
        }
        .process-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(5, 150, 105, 0.4); }
        .process-btn:disabled { background: #9ca3af; cursor: not-allowed; transform: none; box-shadow: none; }
        .progress-container { margin-top: 20px; display: none; }
        .progress-bar { width: 100%; height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; margin-bottom: 10px; }
        .progress-fill { height: 100%; background: linear-gradient(135deg, #059669, #10b981); width: 0%; transition: width 0.3s ease; }
        .progress-text { text-align: center; color: #64748b; font-size: 0.875rem; }
        .results-section { margin-top: 30px; display: none; }
        .results-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .result-card {
            background: white; border-radius: 12px; padding: 25px; text-align: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-left: 4px solid #4f46e5;
        }
        .result-number { font-size: 2.5rem; font-weight: 700; color: #4f46e5; margin-bottom: 5px; }
        .result-label { color: #64748b; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.5px; }
        .action-buttons { display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; }
        .action-btn {
            background: white; color: #4f46e5; border: 2px solid #4f46e5; padding: 12px 24px;
            border-radius: 10px; text-decoration: none; font-weight: 600; transition: all 0.3s ease;
            display: inline-flex; align-items: center; gap: 8px;
        }
        .action-btn:hover { background: #4f46e5; color: white; transform: translateY(-2px); }
        .features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; margin-top: 40px; }
        .feature-card {
            background: white; border-radius: 15px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            text-align: center; transition: all 0.3s ease;
        }
        .feature-card:hover { transform: translateY(-5px); box-shadow: 0 15px 40px rgba(0,0,0,0.15); }
        .feature-icon {
            width: 60px; height: 60px; background: linear-gradient(135deg, #4f46e5, #7c3aed);
            color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center;
            margin: 0 auto 20px; font-size: 1.5rem;
        }
        .feature-card h3 { font-size: 1.25rem; margin-bottom: 15px; color: #1e293b; }
        .feature-card p { color: #64748b; line-height: 1.6; }
        @media (max-width: 768px) {
            .container { padding: 15px; }
            .header h1 { font-size: 2rem; }
            .upload-area { padding: 20px; }
            .file-drop-zone { padding: 40px 15px; }
            .action-buttons { flex-direction: column; align-items: stretch; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>PM Intelligence Dashboard</h1>
            <p>Intelligent project management data ingestion and analysis platform</p>
        </div>

        <div class="main-card">
            <div class="card-header">
                <h2>📁 File Ingestion Interface</h2>
                <p>Upload your project files for intelligent processing and analysis</p>
            </div>

            <div class="upload-area">
                <div class="file-drop-zone" id="dropZone">
                    <div class="upload-icon">📤</div>
                    <div class="upload-text">
                        <h3>Drop files here or click to browse</h3>
                        <p>Supports Excel (.xlsx, .xls), CSV, JSON, PowerPoint (.pptx), and text files</p>
                        <button class="upload-btn" onclick="event.stopPropagation(); document.getElementById('fileInput').click();">
                            Choose Files
                        </button>
                    </div>
                </div>
                
                <input type="file" id="fileInput" class="file-input" multiple 
                       accept=".xlsx,.xls,.csv,.json,.pptx,.txt,.docx">

                <div class="file-list" id="fileList" style="display: none;">
                    <h3 style="margin-bottom: 15px; color: #1e293b;">Selected Files:</h3>
                    <div id="fileItems"></div>
                </div>
            </div>

            <div class="process-section">
                <button class="process-btn" id="processBtn" disabled onclick="processFiles()">
                    🚀 Process Files
                </button>
                
                <div class="progress-container" id="progressContainer">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill"></div>
                    </div>
                    <div class="progress-text" id="progressText">Processing files...</div>
                </div>

                <div class="results-section" id="resultsSection">
                    <div class="results-grid" id="resultsGrid"></div>
                    <div class="action-buttons">
                        <a href="/dashboard" class="action-btn">📊 View Analytics Dashboard</a>
                        <a href="/processed-data-summary" class="action-btn">📋 View Data Summary</a>
                        <button class="action-btn" onclick="resetInterface()">🔄 Process More Files</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-icon">🔍</div>
                <h3>Intelligent Analysis</h3>
                <p>Advanced file processing with smart content extraction and validation for comprehensive project insights.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <h3>Real-time Dashboard</h3>
                <p>Live analytics dashboard with KPI tracking, project health monitoring, and actionable recommendations.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">⚡</div>
                <h3>Fast Processing</h3>
                <p>High-performance file ingestion engine that handles multiple formats with lightning-fast processing speeds.</p>
            </div>
        </div>
    </div>

    <script>
        let selectedFiles = [];
        
        const fileInput = document.getElementById('fileInput');
        const dropZone = document.getElementById('dropZone');
        const fileList = document.getElementById('fileList');
        const fileItems = document.getElementById('fileItems');
        const processBtn = document.getElementById('processBtn');

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            const files = Array.from(e.dataTransfer.files);
            addFiles(files);
        });

        dropZone.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });

        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            if (files.length > 0) {
                addFiles(files);
                e.target.value = '';
            }
        });

        function addFiles(files) {
            files.forEach(file => {
                const existingFile = selectedFiles.find(f => f.name === file.name && f.size === file.size);
                if (!existingFile) {
                    selectedFiles.push(file);
                }
            });
            updateFileList();
        }

        function removeFile(index) {
            selectedFiles.splice(index, 1);
            updateFileList();
        }

        function updateFileList() {
            if (selectedFiles.length === 0) {
                fileList.style.display = 'none';
                processBtn.disabled = true;
                return;
            }

            fileList.style.display = 'block';
            processBtn.disabled = false;

            fileItems.innerHTML = selectedFiles.map((file, index) => {
                const fileExtension = file.name.split('.').pop().toUpperCase();
                const fileSize = formatFileSize(file.size);
                
                return `
                    <div class="file-item">
                        <div class="file-info">
                            <div class="file-icon">${fileExtension}</div>
                            <div class="file-details">
                                <h4>${file.name}</h4>
                                <p>${fileSize}</p>
                            </div>
                        </div>
                        <button class="remove-btn" onclick="removeFile(${index})">Remove</button>
                    </div>
                `;
            }).join('');
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        async function processFiles() {
            if (selectedFiles.length === 0) {
                alert('Please select files first');
                return;
            }

            document.getElementById('progressContainer').style.display = 'block';
            processBtn.disabled = true;
            processBtn.textContent = 'Processing...';

            const formData = new FormData();
            selectedFiles.forEach((file, index) => {
                formData.append('files', file);
            });

            try {
                let progress = 0;
                const progressInterval = setInterval(() => {
                    progress += Math.random() * 15;
                    if (progress > 90) progress = 90;
                    updateProgress(progress);
                }, 500);

                const response = await fetch('/upload-files', {
                    method: 'POST',
                    body: formData
                });

                clearInterval(progressInterval);
                updateProgress(100);

                if (response.ok) {
                    const result = await response.json();
                    showResults(result);
                } else {
                    const errorText = await response.text();
                    throw new Error(`Server error: ${response.status} - ${errorText}`);
                }
            } catch (error) {
                console.error('Error processing files:', error);
                alert(`Error processing files: ${error.message}`);
                resetProcessing();
            }
        }

        function updateProgress(percent) {
            document.getElementById('progressFill').style.width = percent + '%';
            document.getElementById('progressText').textContent = 
                percent < 100 ? `Processing files... ${Math.round(percent)}%` : 'Complete!';
        }

        function showResults(results) {
            const resultsSection = document.getElementById('resultsSection');
            const resultsGrid = document.getElementById('resultsGrid');

            resultsGrid.innerHTML = `
                <div class="result-card">
                    <div class="result-number">${results.total_files || selectedFiles.length}</div>
                    <div class="result-label">Files Processed</div>
                </div>
                <div class="result-card">
                    <div class="result-number">${results.successful_files || 0}</div>
                    <div class="result-label">Successful</div>
                </div>
                <div class="result-card">
                    <div class="result-number">${results.failed_files || 0}</div>
                    <div class="result-label">Failed</div>
                </div>
                <div class="result-card">
                    <div class="result-number">${Math.round((results.successful_files || 0) / selectedFiles.length * 100)}%</div>
                    <div class="result-label">Success Rate</div>
                </div>
            `;

            resultsSection.style.display = 'block';
            
            setTimeout(() => {
                document.getElementById('progressContainer').style.display = 'none';
            }, 1000);
        }

        function resetInterface() {
            selectedFiles = [];
            document.getElementById('fileInput').value = '';
            updateFileList();
            resetProcessing();
            document.getElementById('resultsSection').style.display = 'none';
        }

        function resetProcessing() {
            processBtn.disabled = true;
            processBtn.textContent = '🚀 Process Files';
            document.getElementById('progressContainer').style.display = 'none';
            document.getElementById('progressFill').style.width = '0%';
        }

        updateFileList();
    </script>
</body>
</html>"""
    
    return HTMLResponse(content=html_content)


@app.post("/upload-files")
async def upload_files(files: List[UploadFile] = File(...)):
    """Handle file uploads and processing"""
    try:
        # Save uploaded files
        for file in files:
            storage_manager.save_uploaded_file(file)
        
        # Process files
        results = storage_manager.process_all_uploaded_files()
        return JSONResponse(results)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Processing failed: {str(e)}"}
        )


@app.get("/dashboard", response_class=HTMLResponse)
async def analytics_dashboard():
    """Analytics dashboard with live data"""
    summary = storage_manager.get_processed_data_summary()
    
    dashboard_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PM Intelligence Analytics Dashboard</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1e3a8a 0%, #3730a3 100%);
                min-height: 100vh; color: #333;
            }}
            .header {{
                background: rgba(255,255,255,0.1); backdrop-filter: blur(20px);
                padding: 20px; text-align: center; color: white; margin-bottom: 30px;
            }}
            .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
            .container {{ max-width: 1400px; margin: 0 auto; padding: 0 20px; }}
            .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 25px; margin-bottom: 40px; }}
            .kpi-card {{
                background: white; border-radius: 20px; padding: 30px; text-align: center;
                box-shadow: 0 10px 40px rgba(0,0,0,0.1); transition: all 0.3s ease;
                border-left: 5px solid #4f46e5;
            }}
            .kpi-card:hover {{ transform: translateY(-5px); box-shadow: 0 20px 60px rgba(0,0,0,0.15); }}
            .kpi-icon {{ 
                width: 70px; height: 70px; margin: 0 auto 20px;
                background: linear-gradient(135deg, #4f46e5, #7c3aed); border-radius: 50%;
                display: flex; align-items: center; justify-content: center; font-size: 2rem; color: white;
            }}
            .kpi-value {{ font-size: 3rem; font-weight: 700; color: #1e293b; margin-bottom: 10px; }}
            .kpi-label {{ color: #64748b; font-size: 1rem; text-transform: uppercase; letter-spacing: 1px; }}
            .charts-section {{ background: white; border-radius: 20px; padding: 40px; margin-bottom: 30px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }}
            .section-title {{ font-size: 1.8rem; margin-bottom: 30px; color: #1e293b; text-align: center; }}
            .navigation {{ text-align: center; margin-top: 30px; }}
            .nav-btn {{
                background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white; border: none;
                padding: 15px 30px; border-radius: 12px; font-size: 1rem; margin: 0 10px;
                text-decoration: none; display: inline-block; transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
            }}
            .nav-btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(79, 70, 229, 0.4); }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 PM Intelligence Analytics</h1>
            <p>Real-time insights from your processed project data</p>
        </div>

        <div class="container">
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-icon">📁</div>
                    <div class="kpi-value">{summary.get('total_processed_files', 0)}</div>
                    <div class="kpi-label">Files Processed</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-icon">💾</div>
                    <div class="kpi-value">{summary.get('total_size_mb', 0)}</div>
                    <div class="kpi-label">MB Processed</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-icon">🔄</div>
                    <div class="kpi-value">{summary.get('processing_sessions', 0)}</div>
                    <div class="kpi-label">Processing Sessions</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-icon">✅</div>
                    <div class="kpi-value">Active</div>
                    <div class="kpi-label">System Status</div>
                </div>
            </div>

            <div class="charts-section">
                <h2 class="section-title">📈 Project Intelligence Overview</h2>
                <p style="text-align: center; color: #64748b; font-size: 1.1rem; line-height: 1.6;">
                    Your PM Intelligence system has successfully processed <strong>{summary.get('total_processed_files', 0)} files</strong> 
                    totaling <strong>{summary.get('total_size_mb', 0)} MB</strong> of project data. 
                    The system is actively monitoring and analyzing your project metrics for actionable insights.
                </p>
            </div>

            <div class="navigation">
                <a href="/" class="nav-btn">⬅️ Back to Upload</a>
                <a href="/processed-data-summary" class="nav-btn">📋 View Raw Data</a>
            </div>
        </div>
    </body>
    </html>